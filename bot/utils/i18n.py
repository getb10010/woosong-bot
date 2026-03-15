import json
from pathlib import Path
from typing import Dict

LOCALES_DIR = Path(__file__).parent.parent / "locales"

_translations: Dict[str, Dict[str, str]] = {}


def load_locales():
    global _translations
    for lang in ["kz", "ru", "en"]:
        file_path = LOCALES_DIR / f"{lang}.json"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                _translations[lang] = json.load(f)


def t(key: str, lang: str = "kz", **kwargs) -> str:
    if not _translations:
        load_locales()

    text = _translations.get(lang, {}).get(key)
    if text is None:
        text = _translations.get("kz", {}).get(key, key)

    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text