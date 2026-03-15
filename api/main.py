import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import auth, chat, dm, qa, lost_found, admin, health
from api.websocket.chat import router as ws_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Woosong University KZ API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(dm.router, prefix="/api/dm", tags=["DM"])
app.include_router(qa.router, prefix="/api/qa", tags=["Q&A"])
app.include_router(lost_found.router, prefix="/api/lost-found", tags=["Lost & Found"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(ws_router)


@app.on_event("startup")
async def startup():
    try:
        from db.database import async_engine, Base
        from db.models.user import User
        from db.models.schedule import Schedule
        from db.models.deadline import Deadline
        from db.models.exam import Exam
        from db.models.message import Message
        from db.models.report import Report
        from db.models.anon_dm import AnonDMThread, AnonDMMessage
        from db.models.qa import QAPost, QAAnswer, QAVote
        from db.models.lost_found import LostFound
        from db.models.admin_log import AdminLog
        from db.models.blocked_word import BlockedWord

        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Database init error: {e}")

    logger.info("API started")