"""Language Detection — deterministic text-to-locale mapping.

Invariants:
    - Always returns a valid Locale (never None)
    - Short text (<30 chars) defaults to EN with confidence 0.0
    - DetectorFactory.seed = 0 set at module import (deterministic results)

Design Decisions:
    - langdetect over lingua-py: lighter dependency, pure Python, no binary wheels (ADR: Docker compat)
    - Seed set at module level before any detect() call (ADR: thread-safety note below)
    - Thread safety: Python GIL + asyncio single-thread-per-event-loop means concurrent
      detect() calls are serialized. Safe for FastAPI async handlers.
"""

from langdetect import detect_langs, DetectorFactory

from app.core.domain_types import Locale

# Deterministic: must be set BEFORE any detect() call
DetectorFactory.seed = 0

# langdetect code -> Locale mapping
_CODE_TO_LOCALE: dict[str, Locale] = {
    "en": Locale.EN,
    "pt": Locale.PT_BR,
    "es": Locale.ES,
    "fr": Locale.FR,
    "de": Locale.DE,
    "zh-cn": Locale.ZH,
    "zh-tw": Locale.ZH,
    "ja": Locale.JA,
    "ko": Locale.KO,
    "it": Locale.IT,
    "ru": Locale.RU,
}


def detect_locale(text: str) -> tuple[Locale, float]:
    """Detect the locale of the given text.

    Returns (Locale, confidence) where confidence is 0.0-1.0.
    Short or empty text defaults to (Locale.EN, 0.0).
    Unsupported languages fall back to (Locale.EN, 0.0).
    """
    if not text or len(text.strip()) < 30:
        return Locale.EN, 0.0

    try:
        results = detect_langs(text)
    except Exception:
        return Locale.EN, 0.0

    if not results:
        return Locale.EN, 0.0

    top = results[0]
    locale = _CODE_TO_LOCALE.get(top.lang)
    if locale is None:
        return Locale.EN, 0.0

    return locale, round(top.prob, 4)
