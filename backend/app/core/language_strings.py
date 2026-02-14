"""Language Strings — centralized locale-specific text for agent communication.

Invariants:
    - All strings are pure data (no IO, no computation beyond formatting)
    - Covers all 10 locales in Locale enum
    - Used by system_prompt (bookend), session_agent_stream (prefix), enforce_language (retry)

Design Decisions:
    - Prefix pattern over full prompt translation: 50 strings vs 2600 (ADR: maintenance cost)
    - Bookend strings leverage primacy + recency bias for language anchoring
    - Problem excerpt in prefix re-anchors language after message_history clear on phase transition
    - Retry messages in target locale: asking for Portuguese in English is counterproductive
"""

from app.core.domain_types import Locale

_MAX_PROBLEM_EXCERPT = 200


# --- Bookend closing (appended to system prompt) -----------------------------

_LANGUAGE_BOOKEND_CLOSING: dict[Locale, str] = {
    Locale.EN: (
        "CRITICAL REMINDER: All your text output — every analysis, summary, "
        "explanation, and finding — must be in English."
    ),
    Locale.PT_BR: (
        "LEMBRETE CRITICO: Todo o seu texto de saida — cada analise, resumo, "
        "explicacao e descoberta — deve ser em Portugues Brasileiro."
    ),
    Locale.ES: (
        "RECORDATORIO CRITICO: Todo tu texto de salida — cada analisis, resumen, "
        "explicacion y hallazgo — debe estar en espanol."
    ),
    Locale.FR: (
        "RAPPEL CRITIQUE: Tout votre texte de sortie — chaque analyse, resume, "
        "explication et decouverte — doit etre en francais."
    ),
    Locale.DE: (
        "KRITISCHE ERINNERUNG: Ihre gesamte Textausgabe — jede Analyse, "
        "Zusammenfassung, Erklarung und Erkenntnis — muss auf Deutsch sein."
    ),
    Locale.ZH: (
        "关键提醒：您的所有文本输出——每一项分析、摘要、解释和发现——"
        "都必须使用简体中文。"
    ),
    Locale.JA: (
        "重要リマインダー：すべてのテキスト出力——分析、要約、説明、"
        "発見——は日本語でなければなりません。"
    ),
    Locale.KO: (
        "중요 알림: 모든 텍스트 출력——분석, 요약, 설명, "
        "발견——은 한국어여야 합니다."
    ),
    Locale.IT: (
        "PROMEMORIA CRITICO: Tutto il testo di output — ogni analisi, riassunto, "
        "spiegazione e scoperta — deve essere in italiano."
    ),
    Locale.RU: (
        "КРИТИЧЕСКОЕ НАПОМИНАНИЕ: Весь ваш текстовый вывод — каждый анализ, "
        "резюме, объяснение и открытие — должен быть на русском языке."
    ),
}


# --- Phase instruction prefix (prepended to user messages) --------------------

_PHASE_PREFIX_TEMPLATE: dict[Locale, str] = {
    Locale.EN: (
        "The user provided feedback. Respond in English.\n"
        'Original problem: "{excerpt}"'
    ),
    Locale.PT_BR: (
        "O usuario forneceu feedback. Responda em Portugues Brasileiro.\n"
        'Problema original: "{excerpt}"'
    ),
    Locale.ES: (
        "El usuario proporciono comentarios. Responde en espanol.\n"
        'Problema original: "{excerpt}"'
    ),
    Locale.FR: (
        "L'utilisateur a fourni des commentaires. Repondez en francais.\n"
        'Probleme original: "{excerpt}"'
    ),
    Locale.DE: (
        "Der Benutzer hat Feedback gegeben. Antworten Sie auf Deutsch.\n"
        'Ursprungliches Problem: "{excerpt}"'
    ),
    Locale.ZH: (
        "用户提供了反馈。请用简体中文回答。\n"
        '原始问题："{excerpt}"'
    ),
    Locale.JA: (
        "ユーザーがフィードバックを提供しました。日本語で回答してください。\n"
        '元の問題："{excerpt}"'
    ),
    Locale.KO: (
        "사용자가 피드백을 제공했습니다. 한국어로 답변하세요.\n"
        '원래 문제: "{excerpt}"'
    ),
    Locale.IT: (
        "L'utente ha fornito feedback. Rispondi in italiano.\n"
        'Problema originale: "{excerpt}"'
    ),
    Locale.RU: (
        "Пользователь оставил отзыв. Отвечайте на русском языке.\n"
        'Исходная проблема: "{excerpt}"'
    ),
}


# --- Enforcement retry messages -----------------------------------------------

_LANGUAGE_RETRY_MESSAGE: dict[Locale, str] = {
    Locale.EN: (
        "Please respond in English. Your response was detected as {detected} "
        "(confidence: {confidence}). Rewrite your response in English."
    ),
    Locale.PT_BR: (
        "Por favor, responda em Portugues Brasileiro. Sua resposta foi detectada "
        "como {detected} (confianca: {confidence}). Reescreva em Portugues Brasileiro."
    ),
    Locale.ES: (
        "Por favor, responde en espanol. Tu respuesta fue detectada como {detected} "
        "(confianza: {confidence}). Reescribe tu respuesta en espanol."
    ),
    Locale.FR: (
        "Veuillez repondre en francais. Votre reponse a ete detectee comme {detected} "
        "(confiance: {confidence}). Reecrivez votre reponse en francais."
    ),
    Locale.DE: (
        "Bitte antworten Sie auf Deutsch. Ihre Antwort wurde als {detected} erkannt "
        "(Konfidenz: {confidence}). Schreiben Sie Ihre Antwort auf Deutsch um."
    ),
    Locale.ZH: (
        "请用简体中文回答。您的回答被检测为{detected}"
        "（置信度：{confidence}）。请用简体中文重写您的回答。"
    ),
    Locale.JA: (
        "日本語で回答してください。あなたの回答は{detected}として検出されました"
        "（信頼度：{confidence}）。日本語で回答を書き直してください。"
    ),
    Locale.KO: (
        "한국어로 답변해 주세요. 귀하의 답변은 {detected}로 감지되었습니다"
        "(신뢰도: {confidence}). 한국어로 답변을 다시 작성하세요."
    ),
    Locale.IT: (
        "Si prega di rispondere in italiano. La tua risposta e stata rilevata come "
        "{detected} (confidenza: {confidence}). Riscrivi la tua risposta in italiano."
    ),
    Locale.RU: (
        "Пожалуйста, отвечайте на русском языке. Ваш ответ был определен как "
        "{detected} (уверенность: {confidence}). Перепишите ваш ответ на русском языке."
    ),
}


# --- Public API ---------------------------------------------------------------


def get_bookend_closing(locale: Locale) -> str:
    """Get closing language reminder for system prompt bookend pattern.

    Appended after the base prompt to reinforce language rule via recency bias.
    """
    return _LANGUAGE_BOOKEND_CLOSING[locale]


def get_phase_prefix(locale: Locale, problem: str) -> str:
    """Get locale-aware prefix for phase transition messages.

    Includes a truncated excerpt of the user's original problem to re-anchor
    language context after message_history is cleared on phase transitions.
    """
    if problem and len(problem) > _MAX_PROBLEM_EXCERPT:
        excerpt = problem[:_MAX_PROBLEM_EXCERPT] + "..."
    else:
        excerpt = problem or ""

    template = _PHASE_PREFIX_TEMPLATE[locale]
    return template.format(excerpt=excerpt)


def format_retry_message(
    locale: Locale, detected: str, confidence: float,
) -> str:
    """Format language enforcement retry message in target locale.

    Called by check_response_language() when the agent responds in the wrong
    language. Message is in the TARGET locale (not English) to reinforce
    the desired output language.
    """
    template = _LANGUAGE_RETRY_MESSAGE[locale]
    return template.format(
        detected=detected,
        confidence=f"{confidence:.0%}",
    )
