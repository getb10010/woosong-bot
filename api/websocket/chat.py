import json
import logging
from typing import Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from db.database import async_session
from db.models.user import User
from db.models.message import Message
from api.services.content_filter import check_content
from api.services.rate_limiter import check_rate_limit, check_duplicate_message

router = APIRouter()
logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"User {user_id} connected. Total: {len(self.active_connections)}")

    def disconnect(self, user_id: int):
        self.active_connections.pop(user_id, None)
        logger.info(f"User {user_id} disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict, exclude_user: int = None):
        disconnected = []
        for uid, ws in self.active_connections.items():
            if uid == exclude_user:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(uid)

        for uid in disconnected:
            self.disconnect(uid)

    async def send_to_user(self, user_id: int, message: dict):
        ws = self.active_connections.get(user_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(user_id)


manager = ConnectionManager()


@router.websocket("/ws/chat/{tg_id}")
async def chat_websocket(websocket: WebSocket, tg_id: int):
    # Пайдаланушыны тексеру
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.tg_id == tg_id)
        )
        user = result.scalar_one_or_none()

    if not user or user.is_banned:
        await websocket.close(code=4003)
        return

    await manager.connect(websocket, user.id)

    try:
        while True:
            data = await websocket.receive_text()

            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON"})
                continue

            msg_type = payload.get("type", "message")

            if msg_type == "message":
                content = payload.get("content", "").strip()
                reply_to = payload.get("reply_to_id")

                if not content:
                    await websocket.send_json({"error": "Empty message"})
                    continue

                # Rate limit
                allowed = await check_rate_limit(user.id, "ws_chat", 50, 3600)
                if not allowed:
                    await websocket.send_json({"error": "Rate limit exceeded"})
                    continue

                cooldown = await check_rate_limit(user.id, "ws_cooldown", 1, 5)
                if not cooldown:
                    await websocket.send_json({"error": "Wait 5 seconds"})
                    continue

                # Duplicate check
                is_dupe = await check_duplicate_message(user.id, content)
                if is_dupe:
                    await websocket.send_json({"error": "Duplicate message"})
                    continue

                # Content filter
                filter_result = check_content(content)
                if not filter_result["allowed"]:
                    await websocket.send_json({
                        "error": f"Blocked: {filter_result['reason']}"
                    })
                    continue

                # DB-ге сақтау
                async with async_session() as session:
                    msg = Message(
                        user_id=user.id,
                        content=content,
                        reply_to_id=reply_to,
                    )
                    session.add(msg)
                    await session.commit()
                    await session.refresh(msg)

                    broadcast_data = {
                        "type": "new_message",
                        "data": {
                            "id": msg.id,
                            "content": msg.content,
                            "reply_to_id": msg.reply_to_id,
                            "created_at": msg.created_at.isoformat(),
                        },
                    }

                await manager.broadcast(broadcast_data)

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(user.id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user.id}: {e}")
        manager.disconnect(user.id)