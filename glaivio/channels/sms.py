import uvicorn
from fastapi import FastAPI, Form
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse


class SMSChannel:
    """
    SMS channel via Twilio.
    Exposes a webhook at POST /webhook/sms.
    """

    def start(self, agent, port: int = 8000):
        app = FastAPI(title="Glaivio — SMS")

        @app.post("/webhook/sms")
        async def inbound(From: str = Form(...), Body: str = Form(...)):
            reply = agent.reply(user_id=From, message=Body.strip())
            twiml = MessagingResponse()
            twiml.message(reply)
            return Response(content=str(twiml), media_type="text/xml")

        @app.delete("/session/{user_id}")
        async def clear(user_id: str):
            agent.reset(user_id)
            return {"cleared": user_id}

        print(f"Glaivio SMS agent running on port {port}")
        print(f"Webhook: POST http://localhost:{port}/webhook/sms")
        uvicorn.run(app, host="0.0.0.0", port=port)
