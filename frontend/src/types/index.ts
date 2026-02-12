/* Domain types — mirrors backend ubiquitous language. */

export interface Session {
  id: string;
  problem: string;
  status: "created" | "active" | "resolved" | "cancelled";
  created_at: string;
  resolved_at: string | null;
  total_tokens_used: number;
}

export interface Premise {
  id?: string;
  title: string;
  body: string;
  premise_type: "initial" | "conservative" | "radical" | "combination";
  violated_axiom?: string | null;
  cross_domain_source?: string | null;
  score?: number | null;
  user_comment?: string | null;
  is_winner?: boolean;
}

export interface PremiseScore {
  premise_title: string;
  score: number;
  comment?: string;
}

export interface WinnerInfo {
  title: string;
  score: number | null;
  index: number;
}

export interface AskUserOption {
  label: string;
  description?: string;
}

export interface AskUserData {
  question: string;
  options: AskUserOption[];
  allow_free_text?: boolean;
  context?: string;
}

export interface ContextUsage {
  tokens_used: number;
  tokens_limit: number;
  tokens_remaining: number;
  usage_percentage: number;
  estimated_rounds_left: number;
}

export type SSEEventType =
  | "agent_text"
  | "tool_call"
  | "tool_error"
  | "tool_result"
  | "premises"
  | "ask_user"
  | "final_spec"
  | "context_usage"
  | "done"
  | "error"
  | "spec_file_ready";

export interface SSEEvent {
  type: SSEEventType;
  data: unknown;
}

export interface UserInput {
  type: "scores" | "ask_user_response" | "resolved";
  scores?: PremiseScore[];
  response?: string;
  winner?: WinnerInfo;
}
