"""Translation Layer Tests — validates review event translation for non-EN locales.

Invariants:
    - EN locale returns event unchanged (zero overhead)
    - Each review event type translates correct fields
    - IDs, URLs, enums, booleans, numbers, scores are preserved
    - Graceful fallback on translation errors
    - Empty/None data handling
    - Deep copy: original event is never mutated
"""

from unittest.mock import patch, MagicMock

from app.services.translate_review import (
    translate_text, translate_review_event, _cache,
)
from app.core.domain_types import Locale


# --- translate_text -----------------------------------------------------------


def test_translate_text_returns_original_for_en():
    result = translate_text("Hello world", Locale.EN)
    assert result == "Hello world"


def test_translate_text_returns_empty_for_empty():
    assert translate_text("", Locale.PT_BR) == ""
    assert translate_text(None, Locale.PT_BR) == ""


def test_translate_text_returns_empty_for_whitespace_only():
    assert translate_text("   ", Locale.PT_BR) == "   "


@patch("app.services.translate_review.GoogleTranslator")
def test_translate_text_calls_google_for_non_en(mock_cls):
    _cache.clear()
    mock_instance = MagicMock()
    mock_instance.translate.return_value = "Olá mundo"
    mock_cls.return_value = mock_instance
    result = translate_text("Hello world", Locale.PT_BR)
    assert result == "Olá mundo"
    mock_cls.assert_called_once_with(source="auto", target="pt")


@patch("app.services.translate_review.GoogleTranslator")
def test_translate_text_caches_result(mock_cls):
    _cache.clear()
    mock_instance = MagicMock()
    mock_instance.translate.return_value = "Olá"
    mock_cls.return_value = mock_instance
    translate_text("Hello", Locale.PT_BR)
    translate_text("Hello", Locale.PT_BR)  # should hit cache
    assert mock_instance.translate.call_count == 1


@patch("app.services.translate_review.GoogleTranslator")
def test_translate_text_falls_back_on_error(mock_cls):
    _cache.clear()
    mock_instance = MagicMock()
    mock_instance.translate.side_effect = Exception("API error")
    mock_cls.return_value = mock_instance
    result = translate_text("Hello", Locale.PT_BR)
    assert result == "Hello"  # original returned


@patch("app.services.translate_review.GoogleTranslator")
def test_translate_text_falls_back_on_none_result(mock_cls):
    _cache.clear()
    mock_instance = MagicMock()
    mock_instance.translate.return_value = None
    mock_cls.return_value = mock_instance
    result = translate_text("Hello", Locale.PT_BR)
    assert result == "Hello"


# --- translate_review_event dispatcher ----------------------------------------


def test_returns_event_unchanged_for_en():
    event = {"type": "review_decompose", "data": {"fundamentals": ["Test"]}}
    result = translate_review_event(event, Locale.EN)
    assert result is event  # same object, no copy


def test_returns_event_unchanged_for_missing_type():
    event = {"data": {"fundamentals": ["Test"]}}
    result = translate_review_event(event, Locale.PT_BR)
    assert result is event


def test_returns_event_unchanged_for_none_data():
    event = {"type": "review_decompose", "data": None}
    result = translate_review_event(event, Locale.PT_BR)
    assert result is event


def test_returns_event_unchanged_for_unknown_type():
    _cache.clear()
    event = {"type": "agent_text", "data": "some text"}
    result = translate_review_event(event, Locale.PT_BR)
    # deep copy is made but no translation occurs for unknown types
    assert result["data"] == "some text"


# --- review_decompose ---------------------------------------------------------


@patch("app.services.translate_review.GoogleTranslator")
def test_translates_decompose_fundamentals(mock_cls):
    _cache.clear()
    mock_instance = MagicMock()
    mock_instance.translate.side_effect = lambda t: f"[PT]{t}"
    mock_cls.return_value = mock_instance
    event = {
        "type": "review_decompose",
        "data": {
            "fundamentals": ["Core element"],
            "assumptions": [],
            "reframings": [],
        },
    }
    result = translate_review_event(event, Locale.PT_BR)
    assert result["data"]["fundamentals"] == ["[PT]Core element"]


@patch("app.services.translate_review.GoogleTranslator")
def test_translates_assumption_text_preserves_confirmed(mock_cls):
    _cache.clear()
    mock_instance = MagicMock()
    mock_instance.translate.side_effect = lambda t: f"[PT]{t}"
    mock_cls.return_value = mock_instance
    event = {
        "type": "review_decompose",
        "data": {
            "fundamentals": [],
            "assumptions": [
                {"text": "Assumption", "source": "agent", "confirmed": True},
            ],
            "reframings": [],
        },
    }
    result = translate_review_event(event, Locale.PT_BR)
    a = result["data"]["assumptions"][0]
    assert a["text"] == "[PT]Assumption"
    assert a["source"] == "[PT]agent"
    assert a["confirmed"] is True  # preserved


@patch("app.services.translate_review.GoogleTranslator")
def test_translates_reframing_preserves_type_and_selected(mock_cls):
    _cache.clear()
    mock_instance = MagicMock()
    mock_instance.translate.side_effect = lambda t: f"[PT]{t}"
    mock_cls.return_value = mock_instance
    event = {
        "type": "review_decompose",
        "data": {
            "fundamentals": [],
            "assumptions": [],
            "reframings": [{
                "text": "Reframe", "type": "scope_change",
                "reasoning": "Why", "selected": False,
            }],
        },
    }
    result = translate_review_event(event, Locale.PT_BR)
    r = result["data"]["reframings"][0]
    assert r["text"] == "[PT]Reframe"
    assert r["reasoning"] == "[PT]Why"
    assert r["type"] == "scope_change"  # preserved
    assert r["selected"] is False  # preserved


# --- review_explore -----------------------------------------------------------


@patch("app.services.translate_review.GoogleTranslator")
def test_translates_analogies_preserves_starred(mock_cls):
    _cache.clear()
    mock_instance = MagicMock()
    mock_instance.translate.side_effect = lambda t: f"[PT]{t}"
    mock_cls.return_value = mock_instance
    event = {
        "type": "review_explore",
        "data": {
            "morphological_box": None,
            "analogies": [{
                "domain": "Biology", "description": "Desc",
                "target_application": "App",
                "semantic_distance": "far", "starred": True,
            }],
            "contradictions": [],
            "adjacent": [],
        },
    }
    result = translate_review_event(event, Locale.PT_BR)
    a = result["data"]["analogies"][0]
    assert a["domain"] == "[PT]Biology"
    assert a["description"] == "[PT]Desc"
    assert a["target_application"] == "[PT]App"
    assert a["semantic_distance"] == "far"  # preserved
    assert a["starred"] is True  # preserved


@patch("app.services.translate_review.GoogleTranslator")
def test_translates_morphological_box_parameters(mock_cls):
    _cache.clear()
    mock_instance = MagicMock()
    mock_instance.translate.side_effect = lambda t: f"[PT]{t}"
    mock_cls.return_value = mock_instance
    event = {
        "type": "review_explore",
        "data": {
            "morphological_box": {
                "parameters": [
                    {"name": "Material", "values": ["Steel", "Wood"]},
                ],
            },
            "analogies": [],
            "contradictions": [],
            "adjacent": [],
        },
    }
    result = translate_review_event(event, Locale.PT_BR)
    p = result["data"]["morphological_box"]["parameters"][0]
    assert p["name"] == "[PT]Material"
    assert p["values"] == ["[PT]Steel", "[PT]Wood"]


@patch("app.services.translate_review.GoogleTranslator")
def test_translates_contradictions(mock_cls):
    _cache.clear()
    mock_instance = MagicMock()
    mock_instance.translate.side_effect = lambda t: f"[PT]{t}"
    mock_cls.return_value = mock_instance
    event = {
        "type": "review_explore",
        "data": {
            "morphological_box": None,
            "analogies": [],
            "contradictions": [{
                "property_a": "Speed", "property_b": "Safety",
                "description": "Faster means less safe",
            }],
            "adjacent": [],
        },
    }
    result = translate_review_event(event, Locale.PT_BR)
    c = result["data"]["contradictions"][0]
    assert c["property_a"] == "[PT]Speed"
    assert c["property_b"] == "[PT]Safety"
    assert c["description"] == "[PT]Faster means less safe"


@patch("app.services.translate_review.GoogleTranslator")
def test_translates_adjacent_possible(mock_cls):
    _cache.clear()
    mock_instance = MagicMock()
    mock_instance.translate.side_effect = lambda t: f"[PT]{t}"
    mock_cls.return_value = mock_instance
    event = {
        "type": "review_explore",
        "data": {
            "morphological_box": None,
            "analogies": [],
            "contradictions": [],
            "adjacent": [{
                "current_capability": "Manual process",
                "adjacent_possibility": "Automated workflow",
                "prerequisites": ["API access", "Training data"],
            }],
        },
    }
    result = translate_review_event(event, Locale.PT_BR)
    adj = result["data"]["adjacent"][0]
    assert adj["current_capability"] == "[PT]Manual process"
    assert adj["adjacent_possibility"] == "[PT]Automated workflow"
    assert adj["prerequisites"] == ["[PT]API access", "[PT]Training data"]


# --- review_claims ------------------------------------------------------------


@patch("app.services.translate_review.GoogleTranslator")
def test_translates_claim_text_preserves_id_and_confidence(mock_cls):
    _cache.clear()
    mock_instance = MagicMock()
    mock_instance.translate.side_effect = lambda t: f"[PT]{t}"
    mock_cls.return_value = mock_instance
    event = {
        "type": "review_claims",
        "data": {
            "claims": [{
                "claim_text": "Knowledge claim",
                "reasoning": "Because",
                "falsifiability_condition": "If X",
                "confidence": "grounded",
                "claim_id": "abc-123",
                "evidence": [{
                    "url": "https://example.com",
                    "title": "Source",
                    "summary": "Summary",
                    "type": "supporting",
                }],
            }],
        },
    }
    result = translate_review_event(event, Locale.PT_BR)
    c = result["data"]["claims"][0]
    assert c["claim_text"] == "[PT]Knowledge claim"
    assert c["reasoning"] == "[PT]Because"
    assert c["falsifiability_condition"] == "[PT]If X"
    assert c["confidence"] == "grounded"  # preserved
    assert c["claim_id"] == "abc-123"  # preserved
    e = c["evidence"][0]
    assert e["title"] == "[PT]Source"
    assert e["summary"] == "[PT]Summary"
    assert e["url"] == "https://example.com"  # preserved
    assert e["type"] == "supporting"  # preserved


@patch("app.services.translate_review.GoogleTranslator")
def test_translates_review_verdicts_same_as_claims(mock_cls):
    _cache.clear()
    mock_instance = MagicMock()
    mock_instance.translate.side_effect = lambda t: f"[PT]{t}"
    mock_cls.return_value = mock_instance
    event = {
        "type": "review_verdicts",
        "data": {
            "claims": [{
                "claim_text": "Verdict claim",
                "verdict": "accept",
                "qualification": "With caveats",
                "evidence": [],
            }],
        },
    }
    result = translate_review_event(event, Locale.PT_BR)
    c = result["data"]["claims"][0]
    assert c["claim_text"] == "[PT]Verdict claim"
    assert c["qualification"] == "[PT]With caveats"
    assert c["verdict"] == "accept"  # preserved


# --- review_build -------------------------------------------------------------


@patch("app.services.translate_review.GoogleTranslator")
def test_translates_build_gaps_and_negative_knowledge(mock_cls):
    _cache.clear()
    mock_instance = MagicMock()
    mock_instance.translate.side_effect = lambda t: f"[PT]{t}"
    mock_cls.return_value = mock_instance
    event = {
        "type": "review_build",
        "data": {
            "graph": {
                "nodes": [{
                    "id": "n1", "claim_text": "Claim",
                    "confidence": "grounded", "status": "validated",
                }],
                "edges": [{
                    "source": "n1", "target": "n2", "type": "supports",
                }],
            },
            "gaps": ["Gap in knowledge"],
            "negative_knowledge": [{
                "claim_text": "Rejected",
                "rejection_reason": "Weak", "round": 0,
            }],
            "round": 1,
            "max_rounds_reached": False,
        },
    }
    result = translate_review_event(event, Locale.PT_BR)
    assert result["data"]["graph"]["nodes"][0]["claim_text"] == "[PT]Claim"
    assert result["data"]["graph"]["nodes"][0]["id"] == "n1"  # preserved
    assert result["data"]["graph"]["nodes"][0]["confidence"] == "grounded"
    assert result["data"]["graph"]["edges"][0]["type"] == "supports"  # preserved
    assert result["data"]["gaps"] == ["[PT]Gap in knowledge"]
    nk = result["data"]["negative_knowledge"][0]
    assert nk["claim_text"] == "[PT]Rejected"
    assert nk["rejection_reason"] == "[PT]Weak"
    assert nk["round"] == 0  # preserved
    assert result["data"]["round"] == 1  # preserved
    assert result["data"]["max_rounds_reached"] is False  # preserved


# --- knowledge_document -------------------------------------------------------


@patch("app.services.translate_review.GoogleTranslator")
def test_translates_knowledge_document(mock_cls):
    _cache.clear()
    mock_instance = MagicMock()
    mock_instance.translate.return_value = "# Documento\n\nConteúdo traduzido"
    mock_cls.return_value = mock_instance
    event = {
        "type": "knowledge_document",
        "data": "# Document\n\nTranslated content",
    }
    result = translate_review_event(event, Locale.PT_BR)
    assert result["data"] == "# Documento\n\nConteúdo traduzido"


# --- deep copy safety ---------------------------------------------------------


@patch("app.services.translate_review.GoogleTranslator")
def test_does_not_mutate_original_event(mock_cls):
    _cache.clear()
    mock_instance = MagicMock()
    mock_instance.translate.side_effect = lambda t: f"[PT]{t}"
    mock_cls.return_value = mock_instance
    original = {
        "type": "review_decompose",
        "data": {
            "fundamentals": ["Test"],
            "assumptions": [],
            "reframings": [],
        },
    }
    result = translate_review_event(original, Locale.PT_BR)
    assert original["data"]["fundamentals"] == ["Test"]  # unchanged
    assert result["data"]["fundamentals"] == ["[PT]Test"]  # translated copy


# --- locale mapping -----------------------------------------------------------


@patch("app.services.translate_review.GoogleTranslator")
def test_pt_br_maps_to_pt(mock_cls):
    _cache.clear()
    mock_instance = MagicMock()
    mock_instance.translate.return_value = "Olá"
    mock_cls.return_value = mock_instance
    translate_text("Hello", Locale.PT_BR)
    mock_cls.assert_called_with(source="auto", target="pt")


@patch("app.services.translate_review.GoogleTranslator")
def test_zh_maps_to_zh_cn(mock_cls):
    _cache.clear()
    mock_instance = MagicMock()
    mock_instance.translate.return_value = "你好"
    mock_cls.return_value = mock_instance
    translate_text("Hello", Locale.ZH)
    mock_cls.assert_called_with(source="auto", target="zh-CN")


@patch("app.services.translate_review.GoogleTranslator")
def test_es_maps_to_es(mock_cls):
    _cache.clear()
    mock_instance = MagicMock()
    mock_instance.translate.return_value = "Hola"
    mock_cls.return_value = mock_instance
    translate_text("Hello", Locale.ES)
    mock_cls.assert_called_with(source="auto", target="es")
