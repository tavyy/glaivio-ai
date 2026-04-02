import os
import uvicorn
from fastapi import FastAPI, Form
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse


class WhatsAppChannel:
    """
    WhatsApp channel via Twilio.
    Exposes a webhook at POST /webhook/whatsapp.
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

        @app.delete("/session/{user_id}")
        async def clear(user_id: str):
            agent.reset(user_id)
            return {"cleared": user_id}

        print(f"Glaivio WhatsApp agent running on port {port}")
        print(f"Webhook: POST http://localhost:{port}/webhook/whatsapp")
        uvicorn.run(app, host="0.0.0.0", port=port)
