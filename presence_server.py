import asyncio
import json
import time
import websockets
import firebase_admin
from firebase_admin import credentials, db

# ---------- FIREBASE INIT ----------
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    "databaseURL": "https://fastfirebase-51964-default-rtdb.firebaseio.com"
})

# ---------- CONNECTION STATE ----------
connected_users = {}  # { websocket: { "userId": str, "lastPing": float } }
PING_TIMEOUT = 15  # seconds

# ---------- FIREBASE UTILS ----------
def update_presence(user_id, status):
    ref = db.reference(f"presence/{user_id}")
    data = {
        "status": status,
        "lastSeen": int(time.time())
    }
    ref.set(data)
    print(f"🔥 {user_id} -> {status}")

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
    server = await websockets.serve(handle_connection, "0.0.0.0", 8080)
    print("🚀 Presence Server running at ws://0.0.0.0:8080")
    await server.wait_closed()

asyncio.run(main())
