"""Research Agent — delegates web search to Haiku for token-efficient summaries.

Invariants:
    - Opus never sees raw page_content (saves ~98% web search tokens)
    - Haiku always calls web_search before responding (Rule #1 in its prompt)
    - Failed searches return empty result (never error) — Opus decides retry
    - JSON parsing handles Haiku's common formatting quirks

Design Decisions:
    - Haiku + web_search via create_message_raw (ADR: separate betas from Opus)
    - System prompt is cacheble (static per purpose), user message is dynamic
    - Max 3 loop iterations for pause_turn (web_search is server-side, may pause)
    - _parse_haiku_json has 3 fallback levels (direct, regex, raw text)
"""

import json
import logging
import re

from app.infrastructure.anthropic_client import ResilientAnthropicClient

logger = logging.getLogger(__name__)

# Haiku needs web-search beta but NOT 1M-context beta
_HAIKU_BETAS = ["web-search-2025-03-05"]

_WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 5,
}

_PURPOSE_INSTRUCTIONS = {
    "state_of_art": (
        "Find the CURRENT state of this topic. Focus on:\n"
        "- What exists today (products, methods, frameworks)\n"
        "- Recent developments (2024-2026)\n"
        "- Key players and organizations\n"
        "- Quantitative data (market size, adoption rates, benchmarks)"
    ),
    "evidence_for": (
        "Find evidence SUPPORTING the claim or thesis. Focus on:\n"
        "- Empirical studies, experiments, data\n"
        "- Case studies with measurable outcomes\n"
        "- Expert consensus or authoritative statements\n"
        "- Do NOT cherry-pick — include strength of evidence"
    ),
    "evidence_against": (
        "Find evidence CONTRADICTING or CHALLENGING the claim. Focus on:\n"
        "- Counter-examples, failed experiments, negative results\n"
        "- Critics and their specific objections\n"
        "- Alternative explanations for the same data\n"
        "- Known limitations or boundary conditions"
    ),
    "cross_domain": (
        "Find how THIS concept works in a DIFFERENT domain. Focus on:\n"
        "- Structural parallels (not surface similarity)\n"
        "- How the target domain solved analogous problems\n"
        "- Transferable principles or mechanisms\n"
        "- Specific examples with outcomes"
    ),
    "novelty_check": (
        "Determine if this claim ALREADY EXISTS in literature. Focus on:\n"
        "- Prior art: papers, patents, products that say the same thing\n"
        "- If found: cite the earliest/most authoritative source\n"
        "- If NOT found: report that no prior art was identified\n"
        "- Be thorough — check academic AND industry sources"
    ),
    "falsification": (
        "Try to DISPROVE this claim. Actively search for:\n"
        "- Evidence that directly contradicts it\n"
        "- Cases where the claim's predictions failed\n"
        "- Logical or methodological flaws identified by others\n"
        "- If you cannot find disproving evidence, report that honestly"
    ),
}


def _build_system_prompt(purpose: str, max_results: int) -> str:
    """Build Haiku system prompt with purpose-specific search strategy."""
    purpose_text = _PURPOSE_INSTRUCTIONS.get(purpose, _PURPOSE_INSTRUCTIONS["state_of_art"])
    return _PROMPT_TEMPLATE.format(  # nosec B608
        max_results=max_results,
        purpose=purpose,
        purpose_text=purpose_text,
    )


# LLM prompt template — not SQL. B608 false positive suppressed at call site.
_PROMPT_TEMPLATE = """<role>
You are a factual research assistant. You search the web and report ONLY what you find.
You never speculate, infer, or add information beyond what search results contain.
</role>

<rules>
1. SEARCH FIRST. Always call web_search before responding. Never answer from memory.
2. ONLY FACTS FROM RESULTS. Every sentence in your summary must come from a search result.
   If a search result says X, report X. If no result mentions Y, do not mention Y.
3. NO HALLUCINATED URLs. Only include URLs that appeared in actual search results.
   If you cannot find a URL, omit the source entirely — never fabricate one.
4. NO INTERPRETATION. Report findings, not opinions. Wrong: "This proves X."
   Right: "Source A states X (url)."
5. EMPTY IS OK. If search returns no relevant results, return the empty format below.
   Never pad with invented content to seem helpful.
6. MAX {max_results} SOURCES. Select the {max_results} most relevant results.
   Relevance = directly addresses the query, not tangentially related.
7. RECENCY MATTERS. Prefer recent sources (2024-2026) over older ones when available.
8. LANGUAGE. Write the summary in the same language as the query.
</rules>

<output_format>
Return ONLY a JSON object. No markdown, no explanation, no preamble.

Schema:
{{{{
  "summary": "2-3 sentences synthesizing findings. Cite [1], [2] etc.",
  "sources": [
    {{{{
      "id": 1,
      "url": "exact URL from search result",
      "title": "exact title from search result",
      "finding": "1-2 sentences: what THIS source specifically says",
      "date": "publication date if visible, else null"
    }}}}
  ],
  "result_count": <total results found by web_search>,
  "empty": false
}}}}

If NO relevant results found:
{{{{
  "summary": "No relevant results found for this query.",
  "sources": [],
  "result_count": 0,
  "empty": true
}}}}
</output_format>

<search_strategy purpose="{purpose}">
{purpose_text}
</search_strategy>"""


def _build_user_message(
    query: str, purpose: str, instructions: str | None, max_results: int,
) -> str:
    """Build dynamic user message with query + context from Opus."""
    parts = [
        f"Search for: {query}",
        f"Purpose: {purpose}",
    ]
    if instructions:
        parts.append(f"\nAdditional context from the investigator:\n{instructions}")
    parts.append(f"\nReturn up to {max_results} most relevant results.")
    return "\n".join(parts)


def _parse_haiku_json(text: str) -> dict:
    """Extract JSON from Haiku response. Handles markdown wrapping.

    Fallback levels:
    1. Direct JSON.parse
    2. Regex: extract first {...} block
    3. Return raw text as summary with empty sources
    """
    text = text.strip()

    # Level 1: direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Level 2: extract JSON block (handles ```json ... ``` wrapping)
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Level 3: fallback — use raw text as summary
    logger.warning("Haiku returned non-JSON response, using raw text as summary")
    return {
        "summary": text[:500],
        "sources": [],
        "result_count": 0,
        "empty": True,
    }


def _empty_result(reason: str = "Research unavailable.") -> dict:
    """Standard empty result — Opus sees this, decides whether to retry."""
    return {
        "summary": reason,
        "sources": [],
        "result_count": 0,
        "empty": True,
    }


class ResearchAgent:
    """Delegates web search to Haiku — returns structured summaries to Opus."""

    _MAX_PAUSE_TURNS = 3

    def __init__(
        self, anthropic_client: ResilientAnthropicClient,
        model: str = "claude-haiku-4-5-20251001",
        max_tokens: int = 2000,
    ) -> None:
        self.client = anthropic_client
        self.model = model
        self.max_tokens = max_tokens

    async def execute(
        self,
        query: str,
        purpose: str,
        instructions: str | None = None,
        max_results: int = 3,
    ) -> dict:
        """Run Haiku with web_search, return structured summary."""
        system = _build_system_prompt(purpose, max_results)
        user_msg = _build_user_message(query, purpose, instructions, max_results)
        messages = [{"role": "user", "content": user_msg}]

        try:
            responses: list[object] = []
            response = await self._call_with_pause_handling(
                system, messages, responses,
            )
            if response is None:
                return _empty_result("Research timed out after retries.")

            # Extract text from response
            text_parts = [
                b.text for b in response.content
                if getattr(b, "type", None) == "text"
            ]
            if not text_parts:
                return _empty_result("Research returned no text.")

            raw_text = "\n".join(text_parts)
            result = _parse_haiku_json(raw_text)

            # Normalize: ensure required fields exist
            result.setdefault("summary", "")
            result.setdefault("sources", [])
            result.setdefault("result_count", len(result["sources"]))
            result.setdefault("empty", len(result["sources"]) == 0)

            # Track Haiku token usage (informational — not billed to Opus context)
            result["haiku_tokens"] = sum(
                _response_tokens(r) for r in responses
            )
            return result

        except Exception as e:
            logger.error("Research agent failed: %s", e, exc_info=True)
            return _empty_result("Research unavailable. Retry or proceed without.")

    async def _call_with_pause_handling(self, system, messages, responses):
        """Call Haiku API, handling pause_turn for web_search.

        Appends each API response to `responses` for token tracking.
        """
        response = None
        for _ in range(self._MAX_PAUSE_TURNS):
            response = await self.client.create_message_raw(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system,
                tools=[_WEB_SEARCH_TOOL],
                messages=messages,
                betas=_HAIKU_BETAS,
            )
            responses.append(response)
            if response.stop_reason != "pause_turn":
                return response
            # Serialize and continue (web_search may need multiple turns)
            serialized = [
                b.model_dump(exclude_none=True) for b in response.content
            ]
            messages.append({"role": "assistant", "content": serialized})
            messages.append({
                "role": "user",
                "content": "Continue with the search results.",
            })
        return response


def _response_tokens(response: object) -> int:
    """Sum input + output tokens from an API response."""
    usage = getattr(response, "usage", None)
    if not usage:
        return 0
    inp = getattr(usage, "input_tokens", 0) or 0
    out = getattr(usage, "output_tokens", 0) or 0
    return inp + out
