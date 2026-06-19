"""Locale loader for Daily Briefing.

Loads YAML locale files from this directory.
Falls back to English if the requested locale is not found.
"""

from __future__ import annotations

from pathlib import Path

import yaml

_LOCALE_DIR = Path(__file__).parent
_CACHE: dict[str, dict] = {}


def load_locale(lang: str = "en") -> dict:
    """Load a locale by language code.

    Args:
        lang: Language code ('en', 'de'). Defaults to 'en'.

    Returns:
        Dict with all locale strings for that language.
        Falls back to English if the locale file doesn't exist.
    """
    if lang not in _CACHE:
        path = _LOCALE_DIR / f"{lang}.yaml"
        if not path.exists():
            path = _LOCALE_DIR / "en.yaml"  # fallback
        with open(path, encoding="utf-8") as f:
            _CACHE[lang] = yaml.safe_load(f)
    return _CACHE[lang]


def list_locales() -> list[str]:
    """Return list of available locale codes."""
    return sorted(
        f.stem for f in _LOCALE_DIR.glob("*.yaml") if f.stem != "__init__"
    )


def clear_cache() -> None:
    """Clear the locale cache (useful for testing)."""
    _CACHE.clear()
