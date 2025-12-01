from fastapi import FastAPI
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, messaging

# Initialize Firebase Admin
cred = credentials.Certificate("service-account.json")
firebase_admin.initialize_app(cred)

app = FastAPI()

# ----------- MODELS -----------
class NotificationData(BaseModel):
    token: str
    title: str
    body: str
    data: dict | None = None


# ----------- FCM SEND FUNCTION -----------
def send_fcm(token: str, title: str, body: str, data: dict | None = None):
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body
        ),
        data=data if data else {},
        token=token,
    )

    response = messaging.send(message)
    return response


# ----------- API ENDPOINT -----------
@app.post("/send")
async def send_notification(payload: NotificationData):
    try:
        msg_id = send_fcm(
            token=payload.token,
            title=payload.title,
            body=payload.body,
            data=payload.data,
        )
        return {"success": True, "message_id": msg_id}

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/")
async def root():
    return {"status": "FCM Server is running 🚀"}
