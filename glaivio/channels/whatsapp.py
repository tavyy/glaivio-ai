import os
import uvicorn
from fastapi import FastAPI, Form
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse


MISSED_CALL_STATUSES = {"no-answer", "busy", "canceled", "failed"}

MISSED_CALL_TRIGGER = "missed_call"


class WhatsAppChannel:
    """
    WhatsApp channel via Twilio.
    Exposes a webhook at POST /webhook/whatsapp.
    Also handles missed calls at POST /webhook/missed-call.
    """

    def start(self, agent, port: int = 8000):
        app = FastAPI(title="Glaivio — WhatsApp")

        @app.post("/webhook/whatsapp")
        async def inbound(From: str = Form(...), Body: str = Form(...), To: str = Form(default=None)):
            resolved = agent.resolve(To) if hasattr(agent, "resolve") else agent
            user_id = f"{To}:{From}" if hasattr(agent, "resolve") and To else From
            reply = resolved.reply(user_id=user_id, message=Body.strip())
            twiml = MessagingResponse()
            twiml.message(reply)
            return Response(content=str(twiml), media_type="text/xml")

        @app.post("/webhook/operator")
        async def operator(From: str = Form(...), Body: str = Form(...), To: str = Form(default=None)):
            """Inbound messages from the operator — handles learned:/resume: commands."""
            resolved = agent.resolve(To) if hasattr(agent, "resolve") and To else agent
            response = resolved.operator_reply(Body.strip())
            if response:
                twiml = MessagingResponse()
                twiml.message(response)
                return Response(content=str(twiml), media_type="text/xml")
            return await inbound(From=From, Body=Body, To=To)

        @app.post("/webhook/missed-call")
        async def missed_call(
            CallStatus: str = Form(...),
            To: str = Form(...),
            From: str = Form(...),
            CallSid: str = Form(default=""),
        ):
            """
            Twilio status callback endpoint.
            Fires when a call ends — sends a WhatsApp message to the caller
            if the call was missed (no-answer, busy, canceled, failed).

            Set this URL as the 'Status Callback' on your Twilio Voice number.
            """
            if CallStatus not in MISSED_CALL_STATUSES:
                return {"status": "ignored", "CallStatus": CallStatus}

            print(f"[Glaivio] Missed call from {From} to {To} (status={CallStatus})")

            resolved = agent.resolve(To) if hasattr(agent, "resolve") else agent
            user_id = f"{To}:{From}" if hasattr(agent, "resolve") else From

            reply = resolved.reply(user_id=user_id, message=MISSED_CALL_TRIGGER)

            # send via Twilio REST API (not TwiML — this is a status callback)
            account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            auth_token = os.getenv("TWILIO_AUTH_TOKEN")
            if not account_sid or not auth_token:
                print("[Glaivio] Missing TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN — cannot send missed-call reply")
                return {"status": "error", "detail": "Twilio credentials not configured"}

            from twilio.rest import Client
            client = Client(account_sid, auth_token)
            wa_from = To if To.startswith("whatsapp:") else f"whatsapp:{To}"
            wa_to = From if From.startswith("whatsapp:") else f"whatsapp:{From}"
            client.messages.create(body=reply, from_=wa_from, to=wa_to)
            print(f"[Glaivio] Missed-call WhatsApp reply sent to {wa_to}")

            return {"status": "sent", "to": wa_to}

        @app.delete("/session/{user_id}")
        async def clear(user_id: str):
            agent.reset(user_id)
            return {"cleared": user_id}

        print(f"Glaivio WhatsApp agent running on port {port}")
        print(f"Webhook:      POST http://localhost:{port}/webhook/whatsapp")
        print(f"Missed calls: POST http://localhost:{port}/webhook/missed-call")
        uvicorn.run(app, host="0.0.0.0", port=port)
