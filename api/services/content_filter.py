import re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.models.blocked_word import BlockedWord

# Базалық тыйым сөздер (DB-ден толықтырылады)
BASE_BLOCKED = {
    "kz": [],
    "ru": [],
    "en": [],
}


async def load_blocked_words(session: AsyncSession) -> dict:
    result = await session.execute(select(BlockedWord))
    words = result.scalars().all()

    blocked = {"kz": [], "ru": [], "en": [], None: []}
    for w in words:
        lang_key = w.lang if w.lang in blocked else None
        blocked[lang_key].append({
            "word": w.word.lower(),
            "severity": w.severity,
        })
    return blocked


def check_content(text: str, blocked_words: dict = None) -> dict:
    """
    Мазмұнды тексеру.
    Returns: {"allowed": bool, "reason": str, "severity": str}
    """
    text_lower = text.lower().strip()

    # Бос хабарлама
    if not text_lower or len(text_lower) < 1:
        return {"allowed": False, "reason": "empty", "severity": "block"}

    # Тек emoji / бір символ спам
    if len(text_lower) == 1:
        return {"allowed": False, "reason": "too_short", "severity": "block"}

    # Blocked words тексеру
    if blocked_words:
        for lang_words in blocked_words.values():
            if isinstance(lang_words, list):
                for entry in lang_words:
                    word = entry["word"] if isinstance(entry, dict) else entry
                    severity = entry.get("severity", "block") if isinstance(entry, dict) else "block"
                    if word in text_lower:
                        return {
                            "allowed": False,
                            "reason": f"blocked_word: {word}",
                            "severity": severity,
                        }

    return {"allowed": True, "reason": "", "severity": ""}