import redis.asyncio as redis
from config import settings

_redis = None


async def get_redis():
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.REDIS_URL)
    return _redis


async def check_rate_limit(
    user_id: int,
    action: str,
    max_count: int,
    window_seconds: int,
) -> bool:
    """
    Rate limit тексеру.
    Returns True = рұқсат бар, False = лимит асып кетті
    """
    r = await get_redis()
    key = f"ratelimit:{user_id}:{action}"

    current = await r.get(key)
    if current and int(current) >= max_count:
        return False

    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds)
    await pipe.execute()

    return True


async def check_duplicate_message(user_id: int, content: str) -> bool:
    """
    Бірдей хабарламаны тексеру.
    Returns True = дубликат, False = жаңа хабарлама
    """
    r = await get_redis()
    key = f"lastmsg:{user_id}"

    last = await r.get(key)
    if last and last.decode() == content:
        count_key = f"dupecount:{user_id}"
        count = await r.incr(count_key)
        await r.expire(count_key, 300)  # 5 мин
        if count >= 3:
            return True

    await r.setex(key, 60, content)  # 1 мин сақтау
    return False