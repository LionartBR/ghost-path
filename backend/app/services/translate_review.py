"""Review Event Translation — translates agent-generated review data to user's locale.

Invariants:
    - Only translates review events (review_decompose, review_explore, review_claims,
      review_verdicts, review_build, knowledge_document)
    - If locale is EN, returns event unchanged (zero overhead)
    - User input is NEVER translated
    - agent_text streaming is NOT translated
    - URLs, IDs, enums, booleans, numbers, scores are NEVER translated
    - Falls back to original text on any translation error (graceful degradation)

Design Decisions:
    - deep-translator GoogleTranslator: free, no API key, fast (~100-200ms/call)
    - Per-field translation with try/except: if one field fails, others still translate
    - In-memory cache (module-level dict): reduces API calls for repeated strings
      (ADR: hackathon — single-process, cache lost on restart, acceptable)
    - Locale-to-lang mapping needed: Locale.PT_BR="pt-BR" but GoogleTranslator wants "pt"
"""

import copy
import logging

from deep_translator import GoogleTranslator

from app.core.domain_types import Locale

logger = logging.getLogger(__name__)

# --- Locale-to-GoogleTranslator mapping ------------------------------------
# ADR: Locale enum values (e.g. "pt-BR") don't always match Google's codes ("pt")
_LOCALE_TO_LANG: dict[str, str] = {
    "en": "en",
    "pt-BR": "pt",
    "es": "es",
    "fr": "fr",
    "de": "de",
    "zh": "zh-CN",
    "ja": "ja",
    "ko": "ko",
    "it": "it",
    "ru": "ru",
}

# --- Translation cache (module-level, lost on restart) ---------------------
# ADR: hackathon — single-process uvicorn, no multi-worker, acceptable
# Key: (text, lang_code), Value: translated text
_cache: dict[tuple[str, str], str] = {}


def translate_text(text: str | None, locale: Locale) -> str:
    """Translate a single string to the target locale.

    Returns original text on error, empty/None, or EN locale.
    Uses in-memory cache to avoid redundant API calls.
    """
    if not text or not text.strip():
        return text or ""
    if locale == Locale.EN:
        return text

    lang = _LOCALE_TO_LANG.get(locale.value, "en")
    if lang == "en":
        return text

    cache_key = (text, lang)
    if cache_key in _cache:
        return _cache[cache_key]

    try:
        result = GoogleTranslator(source="auto", target=lang).translate(text)
        if result:
            _cache[cache_key] = result
            return result
        return text
    except Exception as e:
        logger.warning("Translation failed (locale=%s): %s", locale.value, e)
        return text  # graceful fallback to original


def translate_review_event(event: dict, locale: Locale) -> dict:
    """Translate a review SSE event to the target locale.

    Early-returns unchanged event if locale is EN.
    Dispatches to per-event-type translator.
    Returns deep copy to avoid mutating ForgeState.
    """
    if locale == Locale.EN:
        return event

    etype = event.get("type")
    data = event.get("data")
    if not etype or data is None:
        return event

    translated = copy.deepcopy(event)

    match etype:
        case "review_decompose":
            translated["data"] = _translate_decompose(translated["data"], locale)
        case "review_explore":
            translated["data"] = _translate_explore(translated["data"], locale)
        case "review_claims" | "review_verdicts":
            translated["data"] = _translate_claims(translated["data"], locale)
        case "review_build":
            translated["data"] = _translate_build(translated["data"], locale)
        case "knowledge_document":
            translated["data"] = translate_text(str(data), locale)

    return translated


def _translate_decompose(data: dict, locale: Locale) -> dict:
    """Translate review_decompose event data.

    Translates: fundamentals[], assumptions[].text/.source,
                reframings[].text/.reasoning
    Preserves: assumptions[].confirmed, reframings[].type, reframings[].selected
    """
    if "fundamentals" in data and isinstance(data["fundamentals"], list):
        data["fundamentals"] = [
            translate_text(f, locale) for f in data["fundamentals"]
        ]

    for assumption in data.get("assumptions", []):
        if "text" in assumption:
            assumption["text"] = translate_text(assumption["text"], locale)
        if "source" in assumption:
            assumption["source"] = translate_text(assumption["source"], locale)
        # SKIP: "confirmed" (bool)

    for reframing in data.get("reframings", []):
        if "text" in reframing:
            reframing["text"] = translate_text(reframing["text"], locale)
        if "reasoning" in reframing:
            reframing["reasoning"] = translate_text(reframing["reasoning"], locale)
        # SKIP: "type" (enum: scope_change, entity_question, etc.)
        # SKIP: "selected" (bool)

    return data


def _translate_explore(data: dict, locale: Locale) -> dict:
    """Translate review_explore event data.

    Translates: morphological_box params, analogies, contradictions, adjacent
    Preserves: semantic_distance, starred
    """
    mb = data.get("morphological_box")
    if mb and isinstance(mb, dict):
        for param in mb.get("parameters", []):
            if "name" in param:
                param["name"] = translate_text(param["name"], locale)
            if "values" in param and isinstance(param["values"], list):
                param["values"] = [
                    translate_text(v, locale) for v in param["values"]
                ]

    for analogy in data.get("analogies", []):
        for key in ("domain", "target_application", "description"):
            if key in analogy:
                analogy[key] = translate_text(analogy[key], locale)
        # SKIP: "semantic_distance" (enum: near/medium/far)
        # SKIP: "starred" (bool)

    for contradiction in data.get("contradictions", []):
        for key in ("property_a", "property_b", "description"):
            if key in contradiction:
                contradiction[key] = translate_text(
                    contradiction[key], locale,
                )

    for adj in data.get("adjacent", []):
        for key in ("current_capability", "adjacent_possibility"):
            if key in adj:
                adj[key] = translate_text(adj[key], locale)
        if "prerequisites" in adj and isinstance(adj["prerequisites"], list):
            adj["prerequisites"] = [
                translate_text(p, locale) for p in adj["prerequisites"]
            ]

    return data


def _translate_claims(data: dict, locale: Locale) -> dict:
    """Translate review_claims / review_verdicts event data.

    Translates: claim_text, reasoning, falsifiability_condition, qualification,
                evidence[].title, evidence[].summary
    Preserves: claim_id, confidence, builds_on_claim_id, verdict,
               evidence[].url, evidence[].type
    """
    for claim in data.get("claims", []):
        for key in (
            "claim_text", "reasoning",
            "falsifiability_condition", "qualification",
        ):
            if key in claim and claim[key]:
                claim[key] = translate_text(claim[key], locale)
        # SKIP: claim_id, confidence, builds_on_claim_id, verdict

        for evidence in claim.get("evidence", []):
            for key in ("title", "summary"):
                if key in evidence and evidence[key]:
                    evidence[key] = translate_text(evidence[key], locale)
            # SKIP: url, type

    return data


def _translate_build(data: dict, locale: Locale) -> dict:
    """Translate review_build event data.

    Translates: graph.nodes[].claim_text/.qualification, gaps[],
                negative_knowledge[].claim_text/.rejection_reason
    Preserves: IDs, enums, scores, round numbers, booleans, all edges
    """
    graph = data.get("graph", {})
    for node in graph.get("nodes", []):
        for key in ("claim_text", "qualification"):
            if key in node and node[key]:
                node[key] = translate_text(node[key], locale)
        # SKIP: id, confidence, status, round_created
    # SKIP: edges (only IDs and enum types)

    if "gaps" in data and isinstance(data["gaps"], list):
        data["gaps"] = [
            translate_text(g, locale) for g in data["gaps"]
        ]

    for nk in data.get("negative_knowledge", []):
        for key in ("claim_text", "rejection_reason"):
            if key in nk and nk[key]:
                nk[key] = translate_text(nk[key], locale)
        # SKIP: round (int)

    # SKIP: round (int), max_rounds_reached (bool)
    return data
