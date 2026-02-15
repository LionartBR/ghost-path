"""Phase Message Strings (Português Brasileiro) — corpo das mensagens injetadas no role user.

Invariants:
    - Espelha exatamente a estrutura de format_messages.py (inglês)
    - Nomes de ferramentas permanecem em inglês (são identificadores de API)
    - Nomes de fases permanecem em inglês (DECOMPOSE, EXPLORE, etc — constantes do enum Phase)

Design Decisions:
    - Arquivo separado de format_messages.py: evita poluir o módulo principal com ~120 linhas
      extras (ADR: localidade + file size limit de 400 linhas do ExMA)
    - Mesmo padrão de system_prompt_pt_br.py: módulo irmão com strings traduzidas
    - Nomes de ferramentas NÃO traduzidos: o modelo chama tools pelo nome exato em inglês
"""

# --- Labels para feedback do usuário ------------------------------------------

LABELS_PT_BR: dict[str, str] = {
    "reviewed_decomposition": "O usuário revisou a decomposição:",
    "assumption_responses": "Respostas aos pressupostos:",
    "custom_argument": "Argumento do usuário:",
    "reframing_responses": "Respostas às reformulações:",
    "selected_reframings": "Reformulações selecionadas: índices",
    "reviewed_exploration": "O usuário revisou a exploração:",
    "analogy_responses": "Respostas às analogias:",
    "starred_analogies": "Analogias marcadas: índices",
    "suggested_domains": "Domínios sugeridos para busca:",
    "added_contradictions": "Contradições adicionadas:",
    "reviewed_claims": "O usuário revisou as afirmações:",
    "claim_n": "Afirmação #{idx}:",
    "claim_resonance": "  Ressonância: {text}",
    "claim_no_resonance": "  Sem ressonância (usuário rejeitou)",
    "custom_argument_claim": "Argumento do usuário sobre a afirmação:",
    "evidence_valid": "  Evidência válida:",
    "counter_example": "  Contra-exemplo:",
    "missing_factor": "  Fator ausente:",
    "additional_evidence": "  Evidência adicional:",
    "rendered_verdicts": "O usuário emitiu veredictos sobre as afirmações:",
    "reason": "  Razão:",
    "qualification": "  Qualificação:",
    "merge_with": "  Fundir com:",
}

# --- Phase digest headers (used by core/phase_digest.py) ----------------------

DIGEST_PHASE1_HEADER = "Achados da Fase 1 (use para derivar domínios de analogia):"
DIGEST_PHASE2_HEADER = "Achados da Fase 2 (use para derivar direções de síntese):"
DIGEST_PHASE3_HEADER = "Afirmações a validar:"
DIGEST_PHASE4_HEADER = "Validação concluída:"
DIGEST_CONTINUE_HEADER = "Contexto acumulado (rodada {round}):"
DIGEST_CRYSTALLIZE_HEADER = "== Fontes do Documento de Conhecimento =="
DIGEST_RESEARCH_HEADER = "Pesquisas da fase anterior:"

# --- Instruções de fase -------------------------------------------------------

INITIAL_BODY = (
    'O usuário submeteu o seguinte problema:\n\n'
    '"{problem}"\n\n'
    'Inicie a Fase 1 (DECOMPOSE). Use web_search para pesquisar o domínio, '
    'depois chame decompose_to_fundamentals, map_state_of_art, '
    'extract_assumptions e reframe_problem (>= 3 reformulações). '
    'Quando terminar com todas as ferramentas de decomposição, apresente '
    'um resumo das suas descobertas para o usuário revisar.'
)

DECOMPOSE_INSTRUCTION = (
    "Prossiga para a Fase 2 (EXPLORE). Construa uma caixa morfológica, "
    "busque >= 2 domínios distantes por analogias (use web_search primeiro), "
    "identifique contradições e mapeie o possível adjacente."
)

EXPLORE_INSTRUCTION = (
    "Prossiga para a Fase 3 (SYNTHESIZE). Para cada direção promissora, "
    "declare uma tese (com evidências), encontre antítese (use web_search), "
    "depois crie uma síntese. Gere até 3 afirmações nesta rodada."
)

CLAIMS_INSTRUCTION = (
    "Prossiga para a Fase 4 (VALIDATE). Para cada afirmação, tente falsificá-la "
    "(use web_search para refutar), verifique novidade (use web_search), "
    "depois pontue cada afirmação."
)

VERDICTS_INSTRUCTION = (
    "Prossiga para a Fase 5 (BUILD). Adicione afirmações aceitas/qualificadas "
    "ao grafo de conhecimento, analise lacunas e apresente a revisão de construção."
)

VERDICTS_ALL_REJECTED = (
    "Todas as afirmações foram rejeitadas. Retornando à Fase 3 (SYNTHESIZE) "
    "para uma nova rodada dialética. Chame get_negative_knowledge "
    "primeiro (Regra #10), revise o que falhou e por quê, depois referencie "
    "pelo menos uma afirmação anterior (Regra #9). Gere até 3 novas "
    "afirmações com uma abordagem fundamentalmente diferente."
)

BUILD_CONTINUE = (
    "O usuário quer continuar com outra rodada. "
    "Volte para a Fase 3 (SYNTHESIZE). Lembre-se: chame "
    "get_negative_knowledge primeiro (Regra #10) e referencie "
    "pelo menos uma afirmação anterior (Regra #9)."
)

BUILD_DEEP_DIVE = (
    "O usuário quer aprofundar na afirmação {claim_id}. "
    "Faça um ciclo focado de EXPLORE -> SYNTHESIZE -> VALIDATE "
    "limitado a esta afirmação apenas."
)

BUILD_RESOLVE = (
    "O usuário está satisfeito com o grafo de conhecimento. "
    "Prossiga para a Fase 6 (CRYSTALLIZE). Gere o Documento "
    "de Conhecimento final com todas as 10 seções usando "
    "generate_knowledge_document."
)

BUILD_INSIGHT = (
    'O usuário quer adicionar seu próprio insight:\n'
    '"{insight}"\n'
    'URLs de evidência: {urls}\n'
    'Chame submit_user_insight para adicionar ao grafo de conhecimento, '
    'depois apresente a revisão de construção atualizada.'
)

UNKNOWN_BUILD = "Decisão de construção desconhecida."
UNKNOWN_INPUT = "Tipo de entrada desconhecido."

# --- Instruções de retomada de sessão (resume) --------------------------------

RESUME_EXPLORE = (
    "Continue a Fase 2 (EXPLORE). Construa uma caixa morfológica, "
    "busque >= 2 domínios distantes por analogias (use web_search primeiro), "
    "identifique contradições e mapeie o possível adjacente."
)

RESUME_SYNTHESIZE = (
    "Continue a Fase 3 (SYNTHESIZE). Para cada direção promissora, "
    "declare uma tese (com evidências), encontre antítese (use web_search), "
    "depois crie uma síntese. Gere até 3 afirmações nesta rodada."
)

RESUME_VALIDATE = (
    "Continue a Fase 4 (VALIDATE). Para cada afirmação, tente falsificá-la "
    "(use web_search para refutar), verifique novidade (use web_search), "
    "depois pontue cada afirmação."
)

RESUME_BUILD = (
    "Continue a Fase 5 (BUILD). Adicione afirmações aceitas/qualificadas "
    "ao grafo de conhecimento, analise lacunas e apresente a revisão de construção."
)

RESUME_CRYSTALLIZE = (
    "Continue a Fase 6 (CRYSTALLIZE). Revise as seções do documento "
    "de trabalho que você construiu. Escreva implementation_guide e "
    "next_frontiers. Refine todas as seções, depois chame "
    "generate_knowledge_document."
)
