"""Tests for _extract_problem_summary and helpers in review_events.py.

Invariants:
    - Markdown syntax stripped from extracted summaries
    - Truncation at word boundary with ellipsis, never mid-word
    - Falls back to problem text if no matching section found
"""

from app.api.routes.review_events import (
    _extract_problem_summary,
    _strip_markdown,
    _truncate_at_word,
)


# -- _strip_markdown ----------------------------------------------------------

def test_strip_headings():
    assert _strip_markdown("# Hello world") == "Hello world"
    assert _strip_markdown("### Heading") == "Heading"


def test_strip_bold():
    assert _strip_markdown("This is **bold** text") == "This is bold text"


def test_strip_italic():
    assert _strip_markdown("This is *italic* text") == "This is italic text"


def test_strip_underscore_bold():
    assert _strip_markdown("__bold__ and _italic_") == "bold and italic"


def test_strip_inline_code():
    assert _strip_markdown("Use `code` here") == "Use code here"


def test_strip_links():
    assert _strip_markdown("[click here](https://example.com)") == "click here"


def test_strip_list_bullets():
    text = "- item one\n- item two"
    result = _strip_markdown(text)
    assert "item one" in result
    assert "-" not in result


def test_strip_numbered_lists():
    text = "1. first\n2. second"
    result = _strip_markdown(text)
    assert "first" in result
    assert "1." not in result


def test_strip_collapses_whitespace():
    assert _strip_markdown("too   many   spaces") == "too many spaces"


def test_strip_combined_markdown():
    text = "## **Bold heading** with [link](url) and `code`"
    result = _strip_markdown(text)
    assert result == "Bold heading with link and code"


# -- _truncate_at_word --------------------------------------------------------

def test_truncate_short_text_unchanged():
    assert _truncate_at_word("short text", 50) == "short text"


def test_truncate_at_word_boundary():
    text = "This is a long sentence that needs truncation"
    result = _truncate_at_word(text, 20)
    assert result.endswith("...")
    assert "truncation" not in result
    # Should truncate at word boundary before limit
    assert len(result) <= 23  # 20 chars + possible word + "..."


def test_truncate_no_mid_word_cut():
    text = "partnership maturation problem solving"
    result = _truncate_at_word(text, 25)
    assert not result.endswith("probl...")
    assert result.endswith("...")


def test_truncate_exact_limit():
    text = "exactly"
    assert _truncate_at_word(text, 7) == "exactly"


# -- _extract_problem_summary -------------------------------------------------

def test_extracts_from_discovery_section():
    markdown = (
        "# Title\n\n"
        "## 1. The Discovery\n\n"
        "A **domestic robot** is not an appliance.\n\n"
        "## 2. Why This Matters\n\n"
        "Context here."
    )
    result = _extract_problem_summary(markdown, "fallback")
    assert result.startswith("A domestic robot")
    assert "**" not in result


def test_extracts_from_why_this_matters_if_no_discovery():
    markdown = (
        "# Title\n\n"
        "## 2. Why This Matters\n\n"
        "Understanding the **context** is key.\n\n"
        "## 3. Reasoning Chain\n\n"
        "More content."
    )
    result = _extract_problem_summary(markdown, "fallback")
    assert result.startswith("Understanding the context")
    assert "**" not in result


def test_falls_back_to_problem_text():
    markdown = "# Just a title with no sections"
    result = _extract_problem_summary(markdown, "My problem text")
    assert result == "My problem text"


def test_fallback_also_truncated_at_word_boundary():
    long_problem = "word " * 60  # 300 chars
    result = _extract_problem_summary("# No sections", long_problem)
    assert result.endswith("...")
    assert len(result) <= 260  # 250 + word + "..."


def test_empty_fallback():
    result = _extract_problem_summary("# No sections", "")
    assert result == ""


def test_no_markdown_in_result():
    markdown = (
        "# Title\n\n"
        "## 1. The Discovery\n\n"
        "# Core Insight: The **Companion Robot** as a _Maturing_ Partner\n\n"
        "A [domestic robot](http://example.com) that makes `coffee`.\n\n"
        "## 2. Why This Matters\n\n"
        "Context."
    )
    result = _extract_problem_summary(markdown, "fallback")
    assert "#" not in result
    assert "**" not in result
    assert "_" not in result
    assert "`" not in result
    assert "](http" not in result
