import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import auth, chat, dm, qa, lost_found, admin, health
from api.websocket.chat import router as ws_router
from db.database import init_db, async_engine, Base

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
    await init_db()
    logger.info("Database initialized")

    from db.models import *  # noqa - барлық моделдерді импорт
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("All tables created successfully")