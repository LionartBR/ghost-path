"""Research Archive Search — keyword-based lookup of past research entries.

Invariants:
    - Pure function: no IO, no async, no DB
    - Case-insensitive substring match in query + summary text
    - AND logic: all keywords must match (in query OR summary combined)
    - Returns entries in reverse chronological order (most recent first)

Design Decisions:
    - Simple substring matching (not fuzzy/semantic) — predictable, fast, testable
    - Token estimate at 300 tokens/result — conservative, includes sources array
    - max_results default 3: balances usefulness vs context cost
    - max_results hard cap at 10: prevents accidental context blowup
"""

_TOKENS_PER_RESULT = 300
_MAX_RESULTS_CAP = 10


def _matches_keywords(entry: dict, keywords: list[str]) -> bool:
    """Check if all keywords match in query or summary (case-insensitive, AND)."""
    text = (entry.get("query", "") + " " + entry.get("summary", "")).lower()
    return all(kw.lower() in text for kw in keywords)


def _estimate_tokens(count: int) -> int:
    """Conservative token estimate for search results."""
    return count * _TOKENS_PER_RESULT


def search_research_archive(
    archive: list[dict],
    keywords: list[str],
    phase: str | None,
    purpose: str | None,
    max_results: int,
) -> dict:
    """Search research archive by keyword, phase, and purpose.

    Returns dict with results, counts, and token estimates.
    """
    max_results = min(max_results, _MAX_RESULTS_CAP)

    # Filter by phase and purpose first
    filtered = archive
    if phase is not None:
        filtered = [e for e in filtered if e.get("phase") == phase]
    if purpose is not None:
        filtered = [e for e in filtered if e.get("purpose") == purpose]

    # Filter by keywords (AND logic)
    if keywords:
        filtered = [e for e in filtered if _matches_keywords(e, keywords)]

    total = len(filtered)

    # Reverse chronological (most recent = last appended = reversed)
    results = list(reversed(filtered))[:max_results]
    returned = len(results)
    tokens = _estimate_tokens(returned)

    return {
        "status": "ok",
        "results": results,
        "total_matches": total,
        "returned": returned,
        "token_estimate": tokens,
        "token_warning": (
            f"~{tokens} tokens added to context "
            f"({returned} results x ~{_TOKENS_PER_RESULT} tokens each)"
        ),
    }
