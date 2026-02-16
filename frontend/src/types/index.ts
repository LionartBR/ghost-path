/* TRIZ domain types — mirrors backend ubiquitous language. */

// --- Session ---

export type SessionStatus =
  | "decomposing" | "exploring" | "synthesizing"
  | "validating" | "building" | "crystallized" | "cancelled";

export type Phase =
  | "decompose" | "explore" | "synthesize"
  | "validate" | "build" | "crystallize";

export interface PhaseTransition {
  from: Phase;
  to: Phase;
}

export interface Session {
  id: string;
  problem: string;
  status: SessionStatus;
  current_phase: number;
  current_round: number;
  locale?: string;
  created_at: string;
  resolved_at: string | null;
  total_tokens_used: number;
}

// --- Claims ---

export type ClaimStatus = "proposed" | "validated" | "rejected" | "qualified" | "superseded";
export type ClaimConfidence = "speculative" | "emerging" | "grounded";
export type VerdictType = "accept" | "reject" | "qualify" | "merge";

export interface ClaimScores {
  novelty: number | null;
  groundedness: number | null;
  falsifiability: number | null;
  significance: number | null;
}

export type ClaimType = "thesis" | "antithesis" | "synthesis" | "user_contributed" | "merged";

export interface Claim {
  claim_text: string;
  claim_type?: ClaimType;
  reasoning?: string;
  falsifiability_condition?: string;
  confidence?: ClaimConfidence;
  evidence?: Evidence[];
  scores?: ClaimScores;
  claim_id?: string;
  builds_on_claim_id?: string;
  verdict?: VerdictType;
  qualification?: string;
  score_reasoning?: string;
  resonance_prompt?: string;
  resonance_options?: string[];
  user_resonance?: number | null;
}

export interface Evidence {
  url: string;
  title: string;
  summary: string;
  type?: "supporting" | "contradicting" | "contextual";
}

// --- Phase 1: Decompose ---

export interface Assumption {
  text: string;
  source?: string;
  options: string[];
  selected_option: number | null;
}

export interface AssumptionResponse {
  assumption_index: number;
  selected_option: number;
  custom_argument?: string;
}

export interface Reframing {
  text: string;
  type: string;
  reasoning?: string;
  selected: boolean;
  resonance_prompt?: string;
  resonance_options?: string[];
  user_resonance?: string | null;
  selected_resonance_option?: number | null;
}

export interface ReframingResponse {
  reframing_index: number;
  selected_option: number;
  custom_argument?: string;
}

export interface DecomposeReviewData {
  fundamentals: string[];
  assumptions: Assumption[];
  reframings: Reframing[];
}

// --- Phase 2: Explore ---

export interface MorphologicalBox {
  parameters: { name: string; values: string[] }[];
}

export interface Analogy {
  domain: string;
  target_application?: string;
  description: string;
  semantic_distance?: string;
  resonated: boolean;
  resonance_prompt?: string;
  resonance_options?: string[];
  user_resonance?: string | null;
  selected_resonance_option?: number | null;
}

export interface AnalogyResponse {
  analogy_index: number;
  selected_option: number;
  custom_argument?: string;
}

export interface Contradiction {
  property_a: string;
  property_b: string;
  description: string;
}

export interface ExploreReviewData {
  morphological_box: MorphologicalBox | null;
  analogies: Analogy[];
  contradictions: Contradiction[];
  adjacent: { current_capability: string; adjacent_possibility: string; prerequisites: string[] }[];
}

// --- Phase 3-4: Claims & Verdicts ---

export interface ClaimFeedback {
  claim_index: number;
  evidence_valid: boolean;
  counter_example?: string;
  synthesis_ignores?: string;
  additional_evidence?: string;
}

export interface ClaimResponse {
  claim_index: number;
  selected_option: number;
  custom_argument?: string;
}

export interface ClaimVerdict {
  claim_index: number;
  verdict: VerdictType;
  rejection_reason?: string;
  qualification?: string;
  merge_with_claim_id?: string;
}

// --- Phase 5: Build ---

export interface GraphNode {
  id: string;
  type: string;
  data: {
    claim_text: string;
    confidence?: string;
    scores: ClaimScores;
    qualification?: string;
    rejection_reason?: string;
    evidence_count: number;
    round_created: number;
  };
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface BuildReviewData {
  graph: GraphData;
  gaps: string[];
  negative_knowledge: { claim_text: string; rejection_reason: string; round: number }[];
  round: number;
  max_rounds_reached: boolean;
}

// --- Context Usage ---

export interface ContextUsage {
  tokens_used: number;
  tokens_limit: number;
  tokens_remaining: number;
  usage_percentage: number;
  input_tokens: number;
  output_tokens: number;
  cache_creation_tokens: number;
  cache_read_tokens: number;
}

// --- Session Completion ---

export interface SessionStats {
  total_rounds: number;
  claims_validated: number;
  claims_rejected: number;
  claims_qualified: number;
  total_claims: number;
  analogies_used: number;
  contradictions_found: number;
  evidence_collected: number;
  fundamentals_identified: number;
  assumptions_examined: number;
  reframings_explored: number;
  graph_nodes: number;
  graph_edges: number;
  total_tokens_used?: number;
  duration_seconds?: number;
}

export interface CompletionData {
  markdown: string;
  stats: SessionStats;
  graph: GraphData;
  problem: string;
  problem_summary?: string;
}

// --- Web Search Results ---

export interface WebSearchResult {
  url: string;
  title: string;
}

// --- Agent Activity (chronological log) ---

export type ActivityItem =
  | { kind: "text"; text: string }
  | { kind: "tool_call"; tool: string; input_preview: string }
  | { kind: "tool_error"; tool: string; error_code: string; message: string }
  | { kind: "web_search"; query: string; results: WebSearchResult[] };

// --- SSE Events ---

export type SSEEventType =
  | "agent_text" | "tool_call" | "tool_error" | "tool_result"
  | "web_search_detail"
  | "review_decompose" | "review_explore" | "review_claims"
  | "review_verdicts" | "review_build"
  | "knowledge_document" | "phase_change"
  | "context_usage" | "done" | "error" | "heartbeat";

export interface SSEEvent {
  type: SSEEventType;
  data: unknown;
}

// --- User Input ---

export type UserInputType =
  | "decompose_review" | "explore_review"
  | "claims_review" | "verdicts" | "build_decision";

export type BuildDecision = "continue" | "deep_dive" | "resolve" | "add_insight";

export interface UserInput {
  type: UserInputType;
  // decompose_review
  assumption_responses?: AssumptionResponse[];
  reframing_responses?: ReframingResponse[];
  selected_reframings?: number[];  // backward compat
  // explore_review
  analogy_responses?: AnalogyResponse[];
  starred_analogies?: number[];  // legacy backward compat field name
  suggested_domains?: string[];
  added_contradictions?: string[];
  // claims_review
  claim_responses?: ClaimResponse[];
  claim_feedback?: ClaimFeedback[];  // backward compat
  // verdicts
  verdicts?: ClaimVerdict[];
  // build_decision
  decision?: BuildDecision;
  deep_dive_claim_id?: string;
  user_insight?: string;
  user_evidence_urls?: string[];
  selected_gaps?: number[];
  continue_direction?: string;
}
