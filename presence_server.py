import asyncio
import json
import time
import os
import websockets
import firebase_admin
from firebase_admin import credentials, db
from firebase_admin import _apps

# ---------- FIREBASE INIT ----------
def init_firebase():
    try:
        # إذا كان Firebase شغال بالفعل، ما نعيد تهيئته
        if not _apps:
            print("🟢 Initializing Firebase...")
            firebase_config = {
                "type": os.getenv("FB_TYPE"),
                "project_id": os.getenv("FB_PROJECT_ID"),
                "private_key_id": os.getenv("FB_PRIVATE_KEY_ID"),
                "private_key": os.getenv("FB_PRIVATE_KEY").replace("\\n", "\n"),
                "client_email": os.getenv("FB_CLIENT_EMAIL"),
                "client_id": os.getenv("FB_CLIENT_ID"),
                "auth_uri": os.getenv("FB_AUTH_URI"),
                "token_uri": os.getenv("FB_TOKEN_URI"),
                "auth_provider_x509_cert_url": os.getenv("FB_AUTH_PROVIDER_CERT_URL"),
                "client_x509_cert_url": os.getenv("FB_CLIENT_CERT_URL")
            }

            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred, {
                "databaseURL": os.getenv("DATABASE_URL")
            })
            print("✅ Firebase initialized successfully.")
        else:
            print("ℹ️ Firebase already initialized.")
    except Exception as e:
        print(f"❌ Firebase init error: {e}")
        time.sleep(5)
        init_firebase()  # إعادة المحاولة تلقائيًا


init_firebase()

# ---------- CONNECTION STATE ----------
connected_users = {}  # { websocket: { "userId": str, "lastPing": float } }
PING_TIMEOUT = 15  # seconds

# ---------- FIREBASE UTILS ----------
def update_presence(user_id, status):
    try:
        ref = db.reference(f"presence/{user_id}")
        data = {
            "status": status,
            "lastSeen": int(time.time())
        }
        ref.set(data)
        print(f"🔥 {user_id} -> {status}")
    except Exception as e:
        print(f"⚠️ Failed to update presence for {user_id}: {e}")
        init_firebase()  # لو حصلت مشكلة يعيد الاتصال

# ---------- MAIN HANDLER ----------
async def handle_connection(websocket):
    try:
        msg = await websocket.recv()
        data = json.loads(msg)
        user_id = data.get("userId")

        if not user_id:
            print("❌ Connection missing userId")
            await websocket.close()
            return

        connected_users[websocket] = {"userId": user_id, "lastPing": time.time()}
        update_presence(user_id, "online")
        print(f"✅ {user_id} connected.")

        async for message in websocket:
            try:
                data = json.loads(message)
                if data.get("type") == "ping":
                    connected_users[websocket]["lastPing"] = time.time()
                    await websocket.send(json.dumps({"type": "pong"}))
                else:
                    print(f"📩 {user_id}: {data}")
            except Exception as e:
                print(f"⚠️ JSON parse error: {e}")

    except websockets.ConnectionClosed:
        pass
    finally:
        if websocket in connected_users:
            user_id = connected_users[websocket]["userId"]
            del connected_users[websocket]
            update_presence(user_id, "offline")
            print(f"🔴 {user_id} disconnected.")

# ---------- HEARTBEAT MONITOR ----------
async def heartbeat_checker():
    while True:
        now = time.time()
        to_remove = []
        for ws, info in list(connected_users.items()):
            if now - info["lastPing"] > PING_TIMEOUT:
                print(f"⏳ {info['userId']} timeout -> offline")
                update_presence(info["userId"], "offline")
                to_remove.append(ws)
        for ws in to_remove:
            del connected_users[ws]
        await asyncio.sleep(5)

# ---------- MAIN ----------
async def main():
    asyncio.create_task(heartbeat_checker())
    while True:
        try:
            server = await websockets.serve(handle_connection, "0.0.0.0", 8080)
            print("🚀 Presence Server running at ws://0.0.0.0:8080")
            await server.wait_closed()
        except Exception as e:
            print(f"💥 Server error: {e}")
            print("🔁 Restarting WebSocket server in 5 seconds...")
            await asyncio.sleep(5)

asyncio.run(main())