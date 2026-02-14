"""Language detection tests — pure tests for detect_locale.

Tests cover:
    - Correct detection for each supported language (long text)
    - Short text defaults to English
    - Empty text returns English
    - Deterministic results (same input -> same output)
    - Unsupported languages fall back to English
"""

from app.core.detect_language import detect_locale
from app.core.domain_types import Locale


# --- Correct detection for supported languages --------------------------------

def test_detects_english_from_long_text():
    text = (
        "The development of artificial intelligence has fundamentally changed "
        "how we approach complex problem-solving in modern organizations."
    )
    locale, confidence = detect_locale(text)
    assert locale == Locale.EN
    assert confidence > 0.5


def test_detects_portuguese_from_long_text():
    text = (
        "O desenvolvimento da inteligencia artificial mudou fundamentalmente "
        "a forma como abordamos a resolucao de problemas complexos nas "
        "organizacoes modernas."
    )
    locale, confidence = detect_locale(text)
    assert locale == Locale.PT_BR
    assert confidence > 0.5


def test_detects_spanish():
    text = (
        "El desarrollo de la inteligencia artificial ha cambiado fundamentalmente "
        "la forma en que abordamos la resolucion de problemas complejos en las "
        "organizaciones modernas."
    )
    locale, confidence = detect_locale(text)
    assert locale == Locale.ES
    assert confidence > 0.5


def test_detects_french():
    text = (
        "Le developpement de l'intelligence artificielle a fondamentalement "
        "change notre approche de la resolution de problemes complexes dans "
        "les organisations modernes."
    )
    locale, confidence = detect_locale(text)
    assert locale == Locale.FR
    assert confidence > 0.5


def test_detects_german():
    text = (
        "Die Entwicklung der kuenstlichen Intelligenz hat grundlegend veraendert "
        "wie wir komplexe Problemloesungen in modernen Organisationen angehen."
    )
    locale, confidence = detect_locale(text)
    assert locale == Locale.DE
    assert confidence > 0.5


def test_detects_japanese():
    text = "人工知能の発展は、現代の組織における複雑な問題解決へのアプローチを根本的に変えました。"
    locale, confidence = detect_locale(text)
    assert locale == Locale.JA
    assert confidence > 0.5


def test_detects_chinese():
    text = "人工智能的发展从根本上改变了我们在现代组织中处理复杂问题解决的方式。"
    locale, confidence = detect_locale(text)
    assert locale == Locale.ZH
    assert confidence > 0.5


def test_detects_korean():
    text = "인공지능의 발전은 현대 조직에서 복잡한 문제 해결에 접근하는 방식을 근본적으로 변화시켰습니다."
    locale, confidence = detect_locale(text)
    assert locale == Locale.KO
    assert confidence > 0.5


# --- Edge cases ---------------------------------------------------------------

def test_short_text_defaults_to_english():
    locale, confidence = detect_locale("Hello world")
    assert locale == Locale.EN
    assert confidence == 0.0


def test_empty_text_returns_english():
    locale, confidence = detect_locale("")
    assert locale == Locale.EN
    assert confidence == 0.0


def test_deterministic_results():
    text = (
        "O desenvolvimento da inteligencia artificial mudou fundamentalmente "
        "a forma como abordamos a resolucao de problemas complexos."
    )
    result1 = detect_locale(text)
    result2 = detect_locale(text)
    assert result1 == result2


def test_unsupported_language_falls_back_to_english():
    # Thai — not in our supported locales
    text = "การพัฒนาปัญญาประดิษฐ์ได้เปลี่ยนแปลงวิธีการแก้ปัญหาที่ซับซ้อนในองค์กรสมัยใหม่อย่างพื้นฐาน"
    locale, confidence = detect_locale(text)
    assert locale == Locale.EN
    assert confidence == 0.0
