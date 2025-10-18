import os
import asyncio
import json
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import credentials, db
import firebase_admin

# ---------------- FASTAPI SETUP ----------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Presence server is running 🚀"}

# ---------------- FIREBASE SETUP ----------------
cred = credentials.Certificate({
    "type": os.getenv("FB_TYPE"),
    "project_id": os.getenv("FB_PROJECT_ID"),
    "private_key_id": os.getenv("FB_PRIVATE_KEY_ID"),
    "private_key": os.getenv("FB_PRIVATE_KEY").replace("\\n", "\n"),
    "client_email": os.getenv("FB_CLIENT_EMAIL"),
    "client_id": os.getenv("FB_CLIENT_ID"),
    "auth_uri": os.getenv("FB_AUTH_URI"),
    "token_uri": os.getenv("FB_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("FB_AUTH_PROVIDER_CERT_URL"),
    "client_x509_cert_url": os.getenv("FB_CLIENT_CERT_URL"),
})
firebase_admin.initialize_app(cred, {
    "databaseURL": os.getenv("DATABASE_URL")
})

# ---------------- PRESENCE SYSTEM ----------------
connected_users = {}
PING_TIMEOUT = 20

def update_presence(user_id: str, status: str):
    ref = db.reference(f"presence/{user_id}")
    ref.set({
        "status": status,
        "lastSeen": int(time.time())
    })
    print(f"🔥 Updated {user_id} → {status}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    user_id = None
    try:
        data = await websocket.receive_text()
        payload = json.loads(data)
        user_id = payload.get("userId")
        if not user_id:
            await websocket.close()
            return

        connected_users[user_id] = websocket
        update_presence(user_id, "online")
        print(f"✅ {user_id} connected")

        while True:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        pass
    finally:
        if user_id:
            connected_users.pop(user_id, None)
            update_presence(user_id, "offline")
            print(f"🔴 {user_id} disconnected")

# ---------------- RUN SERVER ----------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    uvicorn.run("presence_server:app", host="0.0.0.0", port=port)