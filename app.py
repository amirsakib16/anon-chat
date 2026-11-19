import os
import random
import string
from datetime import datetime
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "anon-chat-secret-key-change-me")

# Use threading for broader compatibility (including Vercel)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading", logger=False, engineio_logger=False)

# In-memory store: rooms last only while people are connected
# Structure: { room_code: { "messages": [...], "users": {sid: nickname}, "created": timestamp } }
ROOMS = {}


def generate_room_code(length=6):
    """Generate a short memorable room code."""
    alphabet = string.ascii_uppercase + string.digits
    # Avoid ambiguous characters
    alphabet = alphabet.replace("O", "").replace("0", "").replace("I", "").replace("1", "")
    return "".join(random.choices(alphabet, k=length))


def get_user_count(room_code):
    room = ROOMS.get(room_code)
    if not room:
        return 0
    return len(room["users"])


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("connect")
def handle_connect():
    emit("connected", {"sid": request.sid})


@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid
    # Find and leave any rooms this user was in
    for room_code, room in list(ROOMS.items()):
        if sid in room["users"]:
            nickname = room["users"].pop(sid)
            leave_room(room_code)
            emit(
                "user_left",
                {
                    "nickname": nickname,
                    "user_count": len(room["users"]),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                },
                to=room_code,
            )
            # Clean up empty rooms
            if len(room["users"]) == 0:
                del ROOMS[room_code]


@socketio.on("create_room")
def handle_create_room(data):
    nickname = (data.get("nickname") or "Anon").strip()[:24] or "Anon"
    room_code = generate_room_code()

    # Extremely unlikely collision, but handle it
    while room_code in ROOMS:
        room_code = generate_room_code()

    ROOMS[room_code] = {
        "messages": [],
        "users": {request.sid: nickname},
        "created": datetime.utcnow().isoformat() + "Z",
    }
    join_room(room_code)

    emit(
        "room_joined",
        {
            "room_code": room_code,
            "nickname": nickname,
            "user_count": 1,
            "messages": [],
            "is_creator": True,
        },
    )


@socketio.on("join_room")
def handle_join_room(data):
    nickname = (data.get("nickname") or "Anon").strip()[:24] or "Anon"
    room_code = (data.get("room_code") or "").strip().upper()

    if not room_code:
        emit("error", {"message": "Room code is required"})
        return

    if room_code not in ROOMS:
        # Auto-create if it doesn't exist (convenient UX)
        ROOMS[room_code] = {
            "messages": [],
            "users": {},
            "created": datetime.utcnow().isoformat() + "Z",
        }

    room = ROOMS[room_code]
    room["users"][request.sid] = nickname
    join_room(room_code)

    # Notify others
    emit(
        "user_joined",
        {
            "nickname": nickname,
            "user_count": len(room["users"]),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
        to=room_code,
        include_self=False,
    )

    # Send current state to the joiner
    emit(
        "room_joined",
        {
            "room_code": room_code,
            "nickname": nickname,
            "user_count": len(room["users"]),
            "messages": room["messages"][-100:],  # last 100 messages
            "is_creator": False,
        },
    )


@socketio.on("leave_room")
def handle_leave_room(data):
    room_code = (data.get("room_code") or "").strip().upper()
    if not room_code or room_code not in ROOMS:
        return

    room = ROOMS[room_code]
    nickname = room["users"].pop(request.sid, "Someone")
    leave_room(room_code)

    emit(
        "user_left",
        {
            "nickname": nickname,
            "user_count": len(room["users"]),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
        to=room_code,
    )

    if len(room["users"]) == 0:
        del ROOMS[room_code]


@socketio.on("send_message")
def handle_send_message(data):
    room_code = (data.get("room_code") or "").strip().upper()
    text = (data.get("text") or "").strip()
    image = data.get("image")  # base64 data URL or None
    nickname = (data.get("nickname") or "Anon").strip()[:24]
    encoded = bool(data.get("encoded"))

    if not room_code or room_code not in ROOMS:
        emit("error", {"message": "Room no longer exists"})
        return

    if not text and not image:
        return

    # Limit image size roughly (base64 is ~1.37x larger)
    if image and len(image) > 2_500_000:  # ~1.8 MB image
        emit("error", {"message": "Image too large (max ~1.5 MB)"})
        return

    room = ROOMS[room_code]
    msg = {
        "id": f"{request.sid}-{datetime.utcnow().timestamp()}",
        "nickname": nickname,
        "text": text[:2000] if text else "",
        "image": image,
        "encoded": encoded,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "sid": request.sid,
    }
    room["messages"].append(msg)

    # Keep only recent messages in memory
    if len(room["messages"]) > 200:
        room["messages"] = room["messages"][-150:]

    emit("new_message", msg, to=room_code)


@socketio.on("typing")
def handle_typing(data):
    room_code = (data.get("room_code") or "").strip().upper()
    nickname = (data.get("nickname") or "Someone").strip()[:24]
    is_typing = bool(data.get("is_typing"))

    if room_code and room_code in ROOMS:
        emit(
            "user_typing",
            {"nickname": nickname, "is_typing": is_typing},
            to=room_code,
            include_self=False,
        )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, debug=True, allow_unsafe_werkzeug=True)