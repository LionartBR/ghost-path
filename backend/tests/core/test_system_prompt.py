"""System prompt tests — validates locale-parameterized prompt generation.

Tests cover:
    - English prompt contains language rule XML tag
    - Portuguese prompt contains Portuguese instruction
    - All locales produce different prompts
    - Backward compat constant equals English prompt
"""

from app.core.domain_types import Locale
from app.services.system_prompt import (
    build_system_prompt,
    AGENT_SYSTEM_PROMPT,
    _LANGUAGE_INSTRUCTIONS,
)


def test_english_prompt_contains_language_rule_tag():
    prompt = build_system_prompt(Locale.EN)
    assert "<language_rule>" in prompt
    assert "</language_rule>" in prompt
    assert "English" in prompt


def test_portuguese_prompt_contains_portuguese_instruction():
    prompt = build_system_prompt(Locale.PT_BR)
    assert "Portugues Brasileiro" in prompt


def test_all_locales_produce_different_prompts():
    prompts = set()
    for locale in Locale:
        prompt = build_system_prompt(locale)
        prompts.add(prompt)
    assert len(prompts) == len(Locale)


def test_backward_compat_constant_equals_english():
    assert AGENT_SYSTEM_PROMPT == build_system_prompt(Locale.EN)


def test_all_locales_have_language_instructions():
    for locale in Locale:
        assert locale in _LANGUAGE_INSTRUCTIONS
        assert len(_LANGUAGE_INSTRUCTIONS[locale]) > 10


def test_prompt_contains_base_content():
    prompt = build_system_prompt(Locale.ES)
    # Should contain the base TRIZ prompt content
    assert "Knowledge Creation Engine" in prompt
    assert "<pipeline>" in prompt
    assert "<enforcement_rules>" in prompt


# --- Bookend pattern tests ----------------------------------------------------


def test_system_prompt_has_bookend_for_pt_br():
    prompt = build_system_prompt(Locale.PT_BR)
    assert "<language_rule>" in prompt
    assert "<language_rule_reminder>" in prompt
    # Portuguese text in BOTH opening and closing
    assert prompt.count("Portugu") >= 2


def test_system_prompt_has_bookend_for_all_locales():
    for locale in Locale:
        prompt = build_system_prompt(locale)
        assert "<language_rule>" in prompt
        assert "<language_rule_reminder>" in prompt


def test_bookend_closing_appears_after_base_prompt():
    prompt = build_system_prompt(Locale.PT_BR)
    base_end = prompt.index("</output_guidance>")
    closing = prompt.index("<language_rule_reminder>")
    assert base_end < closing


def test_language_instruction_includes_adaptive_rule():
    prompt = build_system_prompt(Locale.PT_BR)
    # Should mention following the user's language if they switch
    assert "idioma" in prompt.lower() or "language" in prompt.lower()


# --- PT_BR fully translated prompt --------------------------------------------


def test_pt_br_prompt_uses_translated_base():
    prompt = build_system_prompt(Locale.PT_BR)
    # Should contain Portuguese content with accents, NOT English base
    assert "Motor de Criação de Conhecimento" in prompt
    assert "Método Dialético" in prompt
    assert "Falseabilidade" in prompt
    # English base content should NOT be present
    assert "Knowledge Creation Engine" not in prompt
    assert "Dialectical Method (Core Pattern)" not in prompt


def test_pt_br_prompt_keeps_tool_names_in_english():
    prompt = build_system_prompt(Locale.PT_BR)
    # Tool names are API identifiers — must stay in English
    assert "decompose_to_fundamentals" in prompt
    assert "find_antithesis" in prompt
    assert "research" in prompt
    assert "generate_knowledge_document" in prompt


def test_en_prompt_still_uses_english_base():
    prompt = build_system_prompt(Locale.EN)
    assert "Knowledge Creation Engine" in prompt
    assert "Dialectical Method (Core Pattern)" in prompt


def test_other_locales_still_use_english_base():
    for locale in [Locale.ES, Locale.FR, Locale.DE, Locale.ZH]:
        prompt = build_system_prompt(locale)
        assert "Knowledge Creation Engine" in prompt


# --- Working document section tests -----------------------------------------


def test_system_prompt_contains_working_document_section():
    """English prompt includes the <working_document> guidance."""
    prompt = build_system_prompt(Locale.EN)
    assert "<working_document>" in prompt
    assert "update_working_document" in prompt
    assert "implementation_guide" in prompt


def test_system_prompt_pt_br_contains_working_document_section():
    """Portuguese prompt includes the translated working document guidance."""
    prompt = build_system_prompt(Locale.PT_BR)
    assert "<working_document>" in prompt
    assert "update_working_document" in prompt
    assert "implementation_guide" in prompt


# --- Research archive section tests ----------------------------------------


def test_system_prompt_contains_research_archive_section():
    """English prompt includes the <research_archive> guidance."""
    prompt = build_system_prompt(Locale.EN)
    assert "<research_archive>" in prompt
    assert "search_research_archive" in prompt
    assert "Phase digests" in prompt


def test_pt_br_prompt_contains_research_archive_section():
    """Portuguese prompt includes the translated research archive guidance."""
    prompt = build_system_prompt(Locale.PT_BR)
    assert "<research_archive>" in prompt
    assert "search_research_archive" in prompt
