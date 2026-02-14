"""Language Detection — deterministic text-to-locale mapping.

Invariants:
    - Always returns a valid Locale (never None)
    - Short text (<30 chars) defaults to EN with confidence 0.0
    - Falls back to EN if langdetect is unavailable (graceful degradation)

Design Decisions:
    - langdetect over lingua-py: lighter dependency, pure Python, no binary wheels (ADR: Docker compat)
    - Lazy import with try/except: prevents app startup crash if langdetect fails to install
    - Thread safety: Python GIL + asyncio single-thread-per-event-loop means concurrent
      detect() calls are serialized. Safe for FastAPI async handlers.
"""

import logging

from app.core.domain_types import Locale

logger = logging.getLogger(__name__)

try:
    from langdetect import detect_langs, DetectorFactory
    DetectorFactory.seed = 0  # Deterministic: must be set BEFORE any detect() call
    _LANGDETECT_AVAILABLE = True
except ImportError:
    logger.warning("langdetect not installed — language detection disabled, defaulting to EN")
    _LANGDETECT_AVAILABLE = False

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
    if not _LANGDETECT_AVAILABLE or not text or len(text.strip()) < 30:
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
