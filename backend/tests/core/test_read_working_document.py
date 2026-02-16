"""Read Working Document handler tests — verify TOC and section retrieval.

Tests cover:
    - TOC mode: returns section names with word counts
    - TOC mode: empty document returns empty sections dict
    - Full mode: returns specific section content with word count
    - Full mode: unwritten section returns content=None
    - Error: invalid section name
    - No side effects: document_updated_this_phase unchanged

Design Decisions:
    - Handler tested directly by instantiating CrossCuttingHandlers with mock db
    - ForgeState.working_document populated inline per test
    - Uses unittest.mock.AsyncMock for db (handler is read-only, no DB calls)
"""

import pytest
from unittest.mock import AsyncMock

from app.core.forge_state import ForgeState
from app.services.handle_cross_cutting import CrossCuttingHandlers


class FakeSession:
    total_tokens_used = 0
    total_input_tokens = 0
    total_output_tokens = 0
    total_cache_creation_tokens = 0
    total_cache_read_tokens = 0


@pytest.fixture
def db():
    return AsyncMock()


def _make_handler(state: ForgeState, db) -> CrossCuttingHandlers:
    return CrossCuttingHandlers(db, state)


@pytest.mark.asyncio
async def test_read_toc_returns_all_sections_with_word_counts(db):
    """TOC mode: returns word counts for each written section."""
    state = ForgeState()
    state.working_document["core_insight"] = "The key insight is X because Y"
    state.working_document["evidence_base"] = "Source A supports claim one"
    state.working_document["boundaries"] = "This does not apply to Z"
    handler = _make_handler(state, db)
    result = await handler.read_working_document(FakeSession(), {})
    assert result["status"] == "ok"
    assert result["mode"] == "toc"
    assert result["total_sections"] == 9
    assert result["sections"]["core_insight"] == 7
    assert result["sections"]["evidence_base"] == 5
    assert result["sections"]["boundaries"] == 6
    assert len(result["sections"]) == 3


@pytest.mark.asyncio
async def test_read_toc_empty_document(db):
    """TOC mode: empty working document returns empty sections dict."""
    state = ForgeState()
    handler = _make_handler(state, db)
    result = await handler.read_working_document(FakeSession(), {})
    assert result["status"] == "ok"
    assert result["mode"] == "toc"
    assert result["sections"] == {}
    assert result["total_sections"] == 9


@pytest.mark.asyncio
async def test_read_specific_section_returns_content(db):
    """Full mode: returns section content and word count."""
    state = ForgeState()
    content = "Spaced repetition with interleaving improves long-term retention"
    state.working_document["core_insight"] = content
    handler = _make_handler(state, db)
    result = await handler.read_working_document(
        FakeSession(), {"section": "core_insight"},
    )
    assert result["status"] == "ok"
    assert result["mode"] == "full"
    assert result["section"] == "core_insight"
    assert result["content"] == content
    assert result["word_count"] == 7


@pytest.mark.asyncio
async def test_read_missing_section_returns_null(db):
    """Full mode: unwritten section returns content=None."""
    state = ForgeState()
    handler = _make_handler(state, db)
    result = await handler.read_working_document(
        FakeSession(), {"section": "implementation_guide"},
    )
    assert result["status"] == "ok"
    assert result["section"] == "implementation_guide"
    assert result["content"] is None
    assert "not yet written" in result["message"].lower()


@pytest.mark.asyncio
async def test_read_invalid_section_returns_error(db):
    """Invalid section name returns INVALID_SECTION error."""
    state = ForgeState()
    handler = _make_handler(state, db)
    result = await handler.read_working_document(
        FakeSession(), {"section": "nonexistent_section"},
    )
    assert result["status"] == "error"
    assert result["error_code"] == "INVALID_SECTION"


@pytest.mark.asyncio
async def test_read_does_not_mutate_state(db):
    """read_working_document must not set document_updated_this_phase."""
    state = ForgeState()
    state.working_document["core_insight"] = "Some content here"
    assert state.document_updated_this_phase is False
    handler = _make_handler(state, db)
    # Read TOC
    await handler.read_working_document(FakeSession(), {})
    assert state.document_updated_this_phase is False
    # Read specific section
    await handler.read_working_document(
        FakeSession(), {"section": "core_insight"},
    )
    assert state.document_updated_this_phase is False
