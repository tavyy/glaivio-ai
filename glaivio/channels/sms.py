import os
import datetime
import uvicorn
from fastapi import FastAPI, Form
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse
from twilio.twiml.voice_response import VoiceResponse


MISSED_CALL_STATUSES = {"no-answer", "busy", "canceled", "failed"}

MISSED_CALL_TRIGGER = "missed_call"

# guard: minimum call duration in seconds to send SMS (filters robocalls/accidents)
MIN_CALL_DURATION = 5

# guard: rate limit — one missed call SMS per caller per this many hours
MISSED_CALL_RATE_LIMIT_HOURS = 24


class SMSChannel:
    """
    SMS channel via Twilio.
    Exposes a webhook at POST /webhook/sms.
    Also handles missed calls at POST /webhook/missed-call.
    """

    def start(self, agent, port: int = 8000):
        app = FastAPI(title="Glaivio — SMS")
        _missed_call_sent: dict[str, datetime.datetime] = {}  # rate limit tracker

        @app.post("/webhook/sms")
        async def inbound(From: str = Form(...), Body: str = Form(...), To: str = Form(default=None)):
            resolved = agent.resolve(To) if hasattr(agent, "resolve") and To else agent
            user_id = f"{To}:{From}" if hasattr(agent, "resolve") and To else From
            reply = resolved.reply(user_id=user_id, message=Body.strip())
            twiml = MessagingResponse()
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
            Twilio status callback endpoint.
            Fires when a call ends — sends an SMS to the caller
            if the call was missed (no-answer, busy, canceled, failed, or completed with 0 duration).

            Set this URL as the 'Status Callback' on your Twilio Voice number.
            """
            print(f"[Glaivio] Call status callback: {CallStatus} duration={CallDuration} from {From} to {To}")
            is_missed = CallStatus in MISSED_CALL_STATUSES or CallStatus == "completed"
            if not is_missed:
                return {"status": "ignored", "CallStatus": CallStatus}

            dev_mode = os.getenv("GLAIVIO_DEV") == "1"
            resolved = agent.resolve(To) if hasattr(agent, "resolve") else agent
            user_id = f"{To}:{From}" if hasattr(agent, "resolve") else From

            # guard: ignore very short calls (robocalls, accidental dials)
            if not dev_mode and int(CallDuration) < MIN_CALL_DURATION:
                print(f"[Glaivio] Ignored short call ({CallDuration}s) from {From}")
                return {"status": "ignored", "reason": "too_short"}

            # guard: rate limit — one SMS per caller per 24h
            if not dev_mode:
                resolved_memory = getattr(resolved, "memory", None)
                if resolved_memory and hasattr(resolved_memory, "check_missed_call_rate_limit"):
                    if resolved_memory.check_missed_call_rate_limit(From, MISSED_CALL_RATE_LIMIT_HOURS):
                        print(f"[Glaivio] Rate limited missed call from {From} (Postgres)")
                        return {"status": "ignored", "reason": "rate_limited"}
                else:
                    last_sent = _missed_call_sent.get(From)
                    if last_sent:
                        elapsed = (datetime.datetime.now() - last_sent).total_seconds()
                        if elapsed < MISSED_CALL_RATE_LIMIT_HOURS * 3600:
                            print(f"[Glaivio] Rate limited missed call from {From} (last sent {int(elapsed/3600)}h ago)")
                            return {"status": "ignored", "reason": "rate_limited"}

            print(f"[Glaivio] Missed call from {From} to {To} (status={CallStatus})")

            reply = resolved.reply(user_id=user_id, message=MISSED_CALL_TRIGGER)

            account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            auth_token = os.getenv("TWILIO_AUTH_TOKEN")
            if not account_sid or not auth_token:
                print("[Glaivio] Missing TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN — cannot send missed-call reply")
                return {"status": "error", "detail": "Twilio credentials not configured"}

            from twilio.rest import Client
            client = Client(account_sid, auth_token)
            client.messages.create(body=reply, from_=To, to=From)
            resolved_memory = getattr(resolved, "memory", None)
            if resolved_memory and hasattr(resolved_memory, "record_missed_call"):
                resolved_memory.record_missed_call(From, To)
            else:
                _missed_call_sent[From] = datetime.datetime.now()
            print(f"[Glaivio] Missed-call SMS reply sent to {From}")

            return {"status": "sent", "to": From}

        @app.post("/twiml/reject")
        async def reject():
            """
            TwiML endpoint for incoming voice calls.
            Plays a short message then hangs up.
            Twilio fires /webhook/missed-call via status callback after this.
            """
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
