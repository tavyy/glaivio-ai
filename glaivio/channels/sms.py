import os
import datetime
import uvicorn
from fastapi import FastAPI, Form
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse
from twilio.twiml.voice_response import VoiceResponse


MISSED_CALL_STATUSES = {"no-answer", "busy", "canceled", "failed"}

# guard: minimum call duration in seconds to send SMS (filters robocalls/accidents)
MIN_CALL_DURATION = 5

# guard: rate limit — one missed call SMS per caller per this many hours
MISSED_CALL_RATE_LIMIT_HOURS = 24

OPT_OUT_KEYWORDS = {"stop", "unsubscribe", "cancel", "quit", "end"}
OPT_IN_KEYWORDS = {"yes", "y", "ok", "okay", "sure", "yep", "yeah"}


def _consent_message(business_name: str) -> str:
    return (
        f"Hi, this is {business_name}. Sorry we missed your call! "
        f"Reply YES to continue by text or STOP to opt out."
    )


def _opted_out_message() -> str:
    return "You have been unsubscribed. You will not receive further messages. Reply YES to resubscribe."


class SMSChannel:
    """
    SMS channel via Twilio.
    Exposes a webhook at POST /webhook/sms.
    Also handles missed calls at POST /webhook/missed-call.

    TCPA compliance:
    - Missed call sends a consent request (not an AI message)
    - Conversation only starts after explicit YES
    - STOP immediately opts out and blocks further messages
    - Consent state persisted in Postgres (glaivio_sms_consent)
    """

    def start(self, agent, port: int = 8000):
        app = FastAPI(title="Glaivio — SMS")
        _missed_call_sent: dict[str, datetime.datetime] = {}  # in-memory rate limit fallback
        _consent: dict[str, str] = {}  # in-memory consent fallback: number -> status

        def _get_memory(resolved):
            return getattr(resolved, "memory", None)

        def _get_consent(memory, From: str, To: str) -> str:
            """Return consent status: 'pending', 'consented', 'opted_out', or None."""
            if memory and hasattr(memory, "get_sms_consent"):
                return memory.get_sms_consent(From, To)
            return _consent.get(f"{To}:{From}")

        def _set_consent(memory, From: str, To: str, status: str):
            if memory and hasattr(memory, "set_sms_consent"):
                memory.set_sms_consent(From, To, status)
            else:
                _consent[f"{To}:{From}"] = status

        def _send_sms(to: str, from_: str, body: str):
            account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            auth_token = os.getenv("TWILIO_AUTH_TOKEN")
            if not account_sid or not auth_token:
                print("[Glaivio] Missing Twilio credentials — cannot send SMS")
                return
            from twilio.rest import Client
            Client(account_sid, auth_token).messages.create(body=body, from_=from_, to=to)

        @app.post("/webhook/sms")
        async def inbound(From: str = Form(...), Body: str = Form(...), To: str = Form(default=None)):
            resolved = agent.resolve(To) if hasattr(agent, "resolve") and To else agent
            user_id = f"{To}:{From}" if hasattr(agent, "resolve") and To else From
            memory = _get_memory(resolved)
            text = Body.strip().lower()
            twiml = MessagingResponse()

            # handle opt-out at any time
            if text in OPT_OUT_KEYWORDS:
                _set_consent(memory, From, To, "opted_out")
                resolved.reset(user_id)
                print(f"[Glaivio] {From} opted out")
                twiml.message(_opted_out_message())
                return Response(content=str(twiml), media_type="text/xml")

            consent = _get_consent(memory, From, To)

            # pending consent — waiting for YES/STOP
            if consent == "pending":
                if text in OPT_IN_KEYWORDS:
                    _set_consent(memory, From, To, "consented")
                    print(f"[Glaivio] {From} consented to SMS")
                    reply = resolved.reply(user_id=user_id, message="new_sms_conversation")
                else:
                    # resend consent request
                    business_name = getattr(resolved, "name", None) or "us"
                    reply = _consent_message(business_name)
                twiml.message(reply)
                return Response(content=str(twiml), media_type="text/xml")

            # opted out — never reply
            if consent == "opted_out":
                print(f"[Glaivio] {From} is opted out — ignoring message")
                return Response(content=str(MessagingResponse()), media_type="text/xml")

            # consented or unknown (e.g. inbound-initiated conversation) — normal flow
            reply = resolved.reply(user_id=user_id, message=Body.strip())
            twiml.message(reply)
            return Response(content=str(twiml), media_type="text/xml")

        @app.post("/webhook/missed-call")
        async def missed_call(
            CallStatus: str = Form(...),
            To: str = Form(...),
            From: str = Form(...),
            CallSid: str = Form(default=""),
            CallDuration: str = Form(default="0"),
        ):
            """
            Twilio status callback. Sends a TCPA-compliant consent request to the caller.
            Conversation only starts after they reply YES.
            """
            print(f"[Glaivio] Call status callback: {CallStatus} duration={CallDuration} from {From} to {To}")
            is_missed = CallStatus in MISSED_CALL_STATUSES or CallStatus == "completed"
            if not is_missed:
                return {"status": "ignored", "CallStatus": CallStatus}

            dev_mode = os.getenv("GLAIVIO_DEV") == "1"
            resolved = agent.resolve(To) if hasattr(agent, "resolve") else agent
            memory = _get_memory(resolved)

            # guard: ignore very short calls (robocalls, accidental dials)
            if not dev_mode and int(CallDuration) < MIN_CALL_DURATION:
                print(f"[Glaivio] Ignored short call ({CallDuration}s) from {From}")
                return {"status": "ignored", "reason": "too_short"}

            # guard: rate limit — one SMS per caller per 24h
            if not dev_mode:
                if memory and hasattr(memory, "check_missed_call_rate_limit"):
                    if memory.check_missed_call_rate_limit(From, MISSED_CALL_RATE_LIMIT_HOURS):
                        print(f"[Glaivio] Rate limited missed call from {From}")
                        return {"status": "ignored", "reason": "rate_limited"}
                else:
                    last_sent = _missed_call_sent.get(From)
                    if last_sent:
                        elapsed = (datetime.datetime.now() - last_sent).total_seconds()
                        if elapsed < MISSED_CALL_RATE_LIMIT_HOURS * 3600:
                            print(f"[Glaivio] Rate limited missed call from {From}")
                            return {"status": "ignored", "reason": "rate_limited"}

            # check if already opted out
            consent = _get_consent(memory, From, To)
            if consent == "opted_out":
                print(f"[Glaivio] {From} is opted out — skipping missed call SMS")
                return {"status": "ignored", "reason": "opted_out"}

            # send TCPA consent request (not an AI message)
            business_name = getattr(resolved, "name", None) or "us"
            msg = _consent_message(business_name)
            _send_sms(to=From, from_=To, body=msg)

            # mark as pending consent
            _set_consent(memory, From, To, "pending")

            # record for rate limiting
            if memory and hasattr(memory, "record_missed_call"):
                memory.record_missed_call(From, To)
            else:
                _missed_call_sent[From] = datetime.datetime.now()

            print(f"[Glaivio] TCPA consent request sent to {From}")
            return {"status": "sent", "to": From}

        @app.post("/twiml/reject")
        async def reject():
            twiml = VoiceResponse()
            twiml.reject(reason="busy")
            return Response(content=str(twiml), media_type="text/xml")

        @app.delete("/session/{user_id}")
        async def clear(user_id: str):
            agent.reset(user_id)
            return {"cleared": user_id}

        print(f"Glaivio SMS agent running on port {port}")
        print(f"Webhook:      POST http://localhost:{port}/webhook/sms")
        print(f"Missed calls: POST http://localhost:{port}/webhook/missed-call")
        print(f"Voice reject: POST http://localhost:{port}/twiml/reject")
        uvicorn.run(app, host="0.0.0.0", port=port)
