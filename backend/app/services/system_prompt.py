"""Agent System Prompt — phase-scoped behavioral contract for Claude Opus 4.6.

Invariants:
    - build_system_prompt(locale, phase) returns only phase-relevant sections
    - build_system_prompt(locale) without phase returns all sections (backward compat)
    - Phase-scoped prompts save ~2500 tokens/call vs monolithic prompt
    - Language bookend pattern: language rule at TOP + BOTTOM of prompt

Design Decisions:
    - Sections live in system_prompt_sections.py / _pt_br.py (ADR: ExMA 400-line limit)
    - Phase mapping defined here (shared between EN and PT_BR)
    - Prompt caching: within a phase, system prompt is identical every iteration
      — caching works normally. Between phases, prompt changes — cache invalidated.
    - XML tags preserved for reliable parsing by Opus 4.6
"""

from app.core.domain_types import Locale, Phase
from app.core.language_strings import get_bookend_closing
from app.services import system_prompt_sections as _en
from app.services import system_prompt_sections_pt_br as _pt


_LANGUAGE_INSTRUCTIONS: dict[Locale, str] = {
    Locale.EN: (
        "You MUST respond in English. All text output — analysis, summaries, "
        "explanations, findings — must be in English. Tool names and technical "
        "parameters may remain in English. If the user communicates in a "
        "different language, follow their language instead."
    ),
    Locale.PT_BR: (
        "Voce DEVE responder em Portugues Brasileiro. Todo texto de saida — "
        "analises, resumos, explicacoes, descobertas — deve ser em Portugues "
        "Brasileiro. Nomes de ferramentas e parametros tecnicos podem permanecer "
        "em ingles. Se o usuario se comunicar em outro idioma, acompanhe o "
        "idioma dele."
    ),
    Locale.ES: (
        "DEBES responder en espanol. Todo el texto de salida — analisis, "
        "resumenes, explicaciones, hallazgos — debe estar en espanol. Los "
        "nombres de herramientas y parametros tecnicos pueden permanecer en "
        "ingles. Si el usuario se comunica en otro idioma, sigue su idioma."
    ),
    Locale.FR: (
        "Vous DEVEZ repondre en francais. Tout le texte de sortie — analyses, "
        "resumes, explications, decouvertes — doit etre en francais. Les noms "
        "d'outils et parametres techniques peuvent rester en anglais. Si "
        "l'utilisateur communique dans une autre langue, suivez sa langue."
    ),
    Locale.DE: (
        "Sie MUESSEN auf Deutsch antworten. Aller Text — Analysen, "
        "Zusammenfassungen, Erklarungen, Erkenntnisse — muss auf Deutsch sein. "
        "Werkzeugnamen und technische Parameter koennen auf Englisch bleiben. "
        "Wenn der Benutzer in einer anderen Sprache kommuniziert, folgen Sie "
        "seiner Sprache."
    ),
    Locale.ZH: (
        "你必须用简体中文回答。所有文本输出——分析、摘要、解释、发现——"
        "都必须使用简体中文。工具名称和技术参数可以保留英文。"
        "如果用户使用其他语言交流，请跟随用户的语言。"
    ),
    Locale.JA: (
        "日本語で回答してください。すべてのテキスト出力（分析、要約、説明、"
        "発見）は日本語でなければなりません。ツール名と技術パラメータは英語の"
        "ままで構いません。ユーザーが別の言語で通信する場合は、その言語に"
        "従ってください。"
    ),
    Locale.KO: (
        "한국어로 답변해야 합니다. 모든 텍스트 출력(분석, 요약, 설명, 발견)은 "
        "한국어여야 합니다. 도구 이름과 기술 매개변수는 영어로 유지할 수 있습니다. "
        "사용자가 다른 언어로 소통하면 해당 언어를 따르세요."
    ),
    Locale.IT: (
        "DEVI rispondere in italiano. Tutto il testo di output — analisi, "
        "riassunti, spiegazioni, scoperte — deve essere in italiano. I nomi "
        "degli strumenti e i parametri tecnici possono rimanere in inglese. "
        "Se l'utente comunica in un'altra lingua, segui la sua lingua."
    ),
    Locale.RU: (
        "Вы ДОЛЖНЫ отвечать на русском языке. Весь текстовый вывод — анализ, "
        "резюме, объяснения, открытия — должен быть на русском языке. Названия "
        "инструментов и технические параметры могут оставаться на английском. "
        "Если пользователь общается на другом языке, следуйте его языку."
    ),
}


# ---------------------------------------------------------------------------
# Phase -> sections mapping (shared between EN and PT_BR)
# ADR: sections listed here are non-pipeline, non-rules extras per phase
# ---------------------------------------------------------------------------

_PHASE_EXTRA: dict[Phase, tuple[str, ...]] = {
    Phase.DECOMPOSE: (
        "WORKING_DOCUMENT_DECOMPOSE", "ERROR_RECOVERY", "WEB_RESEARCH",
        "TOOL_EFFICIENCY", "CONTEXT_MANAGEMENT", "THINKING_GUIDANCE",
        "OUTPUT_GUIDANCE",
    ),
    Phase.EXPLORE: (
        "WORKING_DOCUMENT_EXPLORE", "ERROR_RECOVERY", "WEB_RESEARCH",
        "RESEARCH_ARCHIVE", "TOOL_EFFICIENCY", "CONTEXT_MANAGEMENT",
        "THINKING_GUIDANCE", "OUTPUT_GUIDANCE",
    ),
    Phase.SYNTHESIZE: (
        "WORKING_DOCUMENT_SYNTHESIZE", "ERROR_RECOVERY", "WEB_RESEARCH",
        "RESEARCH_ARCHIVE", "DIALECTICAL_METHOD", "FALSIFIABILITY",
        "TOOL_EFFICIENCY", "CONTEXT_MANAGEMENT", "THINKING_GUIDANCE",
        "OUTPUT_GUIDANCE",
    ),
    Phase.VALIDATE: (
        "WORKING_DOCUMENT_VALIDATE", "ERROR_RECOVERY", "WEB_RESEARCH",
        "RESEARCH_ARCHIVE", "FALSIFIABILITY", "TOOL_EFFICIENCY",
        "CONTEXT_MANAGEMENT", "THINKING_GUIDANCE", "OUTPUT_GUIDANCE",
    ),
    Phase.BUILD: (
        "WORKING_DOCUMENT_BUILD", "ERROR_RECOVERY", "WEB_RESEARCH",
        "RESEARCH_ARCHIVE", "KNOWLEDGE_GRAPH", "TOOL_EFFICIENCY",
        "CONTEXT_MANAGEMENT", "THINKING_GUIDANCE", "OUTPUT_GUIDANCE",
    ),
    Phase.CRYSTALLIZE: (
        "WORKING_DOCUMENT_CRYSTALLIZE", "RESEARCH_ARCHIVE",
        "TOOL_EFFICIENCY", "CONTEXT_MANAGEMENT",
        "THINKING_GUIDANCE", "OUTPUT_GUIDANCE",
    ),
}

# Phase -> pipeline section constant name
_PHASE_PIPELINE: dict[Phase, str] = {
    Phase.DECOMPOSE: "PIPELINE_DECOMPOSE",
    Phase.EXPLORE: "PIPELINE_EXPLORE",
    Phase.SYNTHESIZE: "PIPELINE_SYNTHESIZE",
    Phase.VALIDATE: "PIPELINE_VALIDATE",
    Phase.BUILD: "PIPELINE_BUILD",
    Phase.CRYSTALLIZE: "PIPELINE_CRYSTALLIZE",
}

# Phase -> rules section constant name (None = no rules for this phase)
_PHASE_RULES: dict[Phase, str | None] = {
    Phase.DECOMPOSE: "RULES_DECOMPOSE",
    Phase.EXPLORE: "RULES_EXPLORE",
    Phase.SYNTHESIZE: "RULES_SYNTHESIZE",
    Phase.VALIDATE: "RULES_VALIDATE",
    Phase.BUILD: "RULES_BUILD",
    Phase.CRYSTALLIZE: None,
}

# Order for full-prompt rules assembly (covers all 15 rules, no duplication)
_FULL_RULES_ORDER = ("RULES_DECOMPOSE", "RULES_EXPLORE", "RULES_SYNTHESIZE", "RULES_VALIDATE")


def _assemble_phase(mod, phase: Phase) -> str:
    """Build phase-scoped prompt from section constants in the given module."""
    parts = [mod.IDENTITY, mod.MISSION]
    pipeline = getattr(mod, _PHASE_PIPELINE[phase])
    parts.append(f"<pipeline>\n{mod.PIPELINE_INTRO}\n\n{pipeline}\n</pipeline>")
    for attr in _PHASE_EXTRA[phase]:
        parts.append(getattr(mod, attr))
    rules_attr = _PHASE_RULES[phase]
    if rules_attr:
        rules = getattr(mod, rules_attr)
        parts.append(
            f"<enforcement_rules>\n{mod.RULES_INTRO}\n\n{rules}\n</enforcement_rules>"
        )
    return "\n\n".join(parts)


def _assemble_full(mod) -> str:
    """Build full prompt with all sections (backward compat, phase=None)."""
    all_pipelines = "\n\n".join(
        getattr(mod, _PHASE_PIPELINE[p]) for p in Phase
    )
    all_rules = "\n\n".join(
        getattr(mod, attr) for attr in _FULL_RULES_ORDER
    )
    parts = [
        mod.IDENTITY, mod.MISSION,
        f"<pipeline>\n{mod.PIPELINE_INTRO}\n\n{all_pipelines}\n</pipeline>",
        mod.WORKING_DOCUMENT,
        f"<enforcement_rules>\n{mod.RULES_INTRO}\n\n{all_rules}\n</enforcement_rules>",
        mod.ERROR_RECOVERY, mod.WEB_RESEARCH, mod.RESEARCH_ARCHIVE,
        mod.DIALECTICAL_METHOD, mod.FALSIFIABILITY, mod.KNOWLEDGE_GRAPH,
        mod.TOOL_EFFICIENCY, mod.CONTEXT_MANAGEMENT, mod.THINKING_GUIDANCE,
        mod.OUTPUT_GUIDANCE,
    ]
    return "\n\n".join(parts)


def _wrap_language(base: str, locale: Locale) -> str:
    """Add language bookend (language rule at top + bottom)."""
    instruction = _LANGUAGE_INSTRUCTIONS[locale]
    closing = get_bookend_closing(locale)
    return (
        f"<language_rule>\n{instruction}\n</language_rule>\n\n"
        f"{base}\n\n"
        f"<language_rule_reminder>\n{closing}\n</language_rule_reminder>"
    )


def build_system_prompt(
    locale: Locale = Locale.EN, phase: Phase | None = None,
) -> str:
    """Build system prompt with optional phase scoping.

    phase=None: full prompt with all sections (backward compat).
    phase=Phase.X: only sections relevant to that phase (~2500 tokens saved).
    """
    mod = _pt if locale == Locale.PT_BR else _en
    base = _assemble_phase(mod, phase) if phase else _assemble_full(mod)
    return _wrap_language(base, locale)


# Backward compat — existing imports still work
AGENT_SYSTEM_PROMPT = build_system_prompt(Locale.EN)
