import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel


class Message(BaseModel):
    user_id: str
    message: str


class WebChannel:
    """
    Web channel — simple HTTP chat interface.
    POST /chat with {user_id, message} → {reply}
    GET / → simple chat UI for testing
    """

    def start(self, agent, port: int = 8000):
        app = FastAPI(title="Glaivio — Web")

        @app.post("/chat")
        async def chat(body: Message):
            reply = agent.reply(user_id=body.user_id, message=body.message)
            return {"reply": reply}

        @app.delete("/session/{user_id}")
        async def clear(user_id: str):
            agent.reset(user_id)
            return {"cleared": user_id}

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        @app.get("/", response_class=HTMLResponse)
        async def ui():
            return """
            <html><body style="font-family:sans-serif;max-width:600px;margin:40px auto">
            <h2>Glaivio Web Chat</h2>
            <div id="log" style="border:1px solid #ccc;padding:10px;height:300px;overflow-y:auto;margin-bottom:10px"></div>
            <input id="msg" style="width:80%;padding:8px" placeholder="Type a message..." />
            <button onclick="send()" style="padding:8px 16px">Send</button>
            <script>
            async function send() {
                const msg = document.getElementById('msg').value;
                document.getElementById('log').innerHTML += '<p><b>You:</b> ' + msg + '</p>';
                document.getElementById('msg').value = '';
                const res = await fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({user_id: 'web-user', message: msg})
                });
                const data = await res.json();
                document.getElementById('log').innerHTML += '<p><b>Agent:</b> ' + data.reply + '</p>';
            }
            document.getElementById('msg').addEventListener('keypress', e => { if(e.key === 'Enter') send(); });
            </script>
            </body></html>
            """

        print(f"Glaivio Web agent running on port {port}")
        print(f"Chat UI:  http://localhost:{port}/")
        print(f"API:      POST http://localhost:{port}/chat")
        uvicorn.run(app, host="0.0.0.0", port=port)
