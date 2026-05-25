export type UiSurface = {
  surface_id: string;
  type: string;
  title: string;
  payload: Record<string, any>;
};

export type PendingAction = {
  action_id: string;
  type: "create_task" | "create_email_draft" | "create_calendar_event";
  title: string;
  payload: Record<string, any>;
  status: "staged" | "approved" | "cancelled";
};

export type AgentState = {
  thread_id?: string;
  session_title?: string;
  created_at?: string;
  updated_at?: string;
  messages?: Array<{ role: "user" | "assistant"; content: string; at?: string }>;
  active_account_id?: string;
  estimated_prompt_tokens?: number;
  compacted_this_turn?: boolean;
  ui_surfaces?: UiSurface[];
  pending_actions?: PendingAction[];
  tool_traces?: Array<{ name: string; ok: boolean; result_preview: string }>;
};

export type ThreadSummary = {
  thread_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  active_account_id?: string | null;
  message_count: number;
  last_message_preview: string;
};

export type ThreadDetail = {
  summary: ThreadSummary;
  snapshot: AgentState;
  messages: Array<{ id: string; role: "user" | "assistant"; content: string }>;
};

export type AccountSummary = {
  account_id: string;
  name: string;
  tier: string;
  owner: string;
  renewal_date: string;
  arr_usd: number;
  health: "healthy" | "watch" | "at_risk";
};
