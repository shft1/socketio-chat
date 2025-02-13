import sys

import eventlet
import socketio
from eventlet import wsgi
from loguru import logger
from pydantic import BaseModel, ConfigDict

ROOMS = ["lobby", "general", "random"]
USERS = {}

# Настройка logger'а Loguru для вывода логов в консоль и файл
loguru_format = "<green>{time}</green> <level>{message}</level>"
logger.remove(0)
logger.add(sys.stdout, colorize=True, level="INFO", format=loguru_format)
logger.add("logs.log", level="INFO")


# Описание моделей pydantic
class Message(BaseModel):
    text: str
    author: str


class User(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    room: str
    name: str
    messages: Message | None = None


# Заставляем работать пути к статике
static_files = {"/": "static/index.html", "/static": "./static"}
sio = socketio.Server(cors_allowed_origins="*", async_mode="eventlet")
app = socketio.WSGIApp(sio, static_files=static_files)


# Обрабатываем подключение пользователя
@sio.event
def connect(sid, environ):
    logger.info(f"Пользователь {sid} подключился")


# Отправляем комнаты
@sio.on("get_rooms")
def on_get_rooms(sid, data):
    sio.emit("rooms", data=ROOMS, to=sid)


@sio.on("join")
def on_join(sid, data):
    USERS[sid] = User(**data)
    sio.save_session(sid, session=data)
    sio.enter_room(sid, room=data["room"])
    sio.emit("move", data={"room": data["room"]}, to=sid)


@sio.on("leave")
def on_leave(sid, data):
    room = sio.get_session(sid).pop("room")
    sio.leave_room(sid, room=room)


# Обрабатываем отправку ответа
@sio.on("send_message")
def on_message(sid, data):
    data["author"] = sio.get_session(sid)["name"]
    USERS[sid].messages = data
    user = USERS[sid]
    sio.emit(
        "message",
        data={"text": user.messages.text, "name": user.name},
        room=user.room,
    )


# Обрабатываем отключение пользователя
@sio.event
def disconnect(sid):
    logger.info(f"Пользователь {sid} отключился")


if __name__ == "__main__":
    wsgi.server(eventlet.listen(("127.0.0.1", 8000)), app)
