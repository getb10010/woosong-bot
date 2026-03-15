import asyncio
from sqlalchemy import select
from db.database import async_session
from db.models.user import User


async def check():
    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        print(f"Users count: {len(users)}")
        for u in users:
            print(f"  ID:{u.id} TG:{u.tg_id} Section:{u.section} Complete:{u.onboarding_complete}")


asyncio.run(check())