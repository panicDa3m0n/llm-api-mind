export type ChatSession = {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
};

export type ChatMessage = {
  id: string;
  session_id: string;
  turn_id: string | null;
  role: "user" | "assistant" | string;
  content: string;
  created_at: string;
  metadata: Record<string, unknown>;
};

export type ChatTurn = {
  session: ChatSession;
  turn_id: string;
  status: string;
  user_message: ChatMessage;
  assistant_message: ChatMessage;
  trace_ids: string[];
  model: string;
  latency_ms: number;
  usage: Record<string, unknown>;
};

export type TraceItem = {
  id: string;
  session_id: string;
  turn_id: string | null;
  kind: string;
  payload: Record<string, unknown>;
  created_at: string;
};

export type CognitiveEvent = {
  id: string;
  session_id: string;
  turn_id: string | null;
  seq: number;
  type: string;
  source: string;
  actor: string;
  visibility: string;
  status: string;
  parent_event_id: string | null;
  trace_id: string | null;
  tool_call_id: string | null;
  message_id: string | null;
  payload: Record<string, unknown>;
  created_at: string;
};

export type StreamEvent = {
  type: string;
  data: StreamEventData;
};

export type StreamEventData = Record<string, unknown> & {
  seq?: number;
  model_step?: number;
  turn_id?: string;
};

export type AgentStep = {
  id: string;
  kind:
    | "thinking"
    | "tool"
    | "result"
    | "answer"
    | "runtime"
    | "memory"
    | "note"
    | "schema"
    | "session"
    | "metacognition";
  seq: number;
  blockId?: string;
  modelStep?: number;
  phase?:
    | "created"
    | "streaming"
    | "captured"
    | "executing"
    | "completed"
    | "persisted"
    | "failed";
  title: string;
  body: string;
  data?: Record<string, unknown>;
  status: "active" | "done" | "error";
};

export type DashboardMemory = {
  id: string;
  type: string;
  scope: string;
  status: string;
  content: string;
  reason_for_storage: string;
  expected_future_use: string | null;
  confidence: number;
  salience: number;
  usage_count: number;
  source_session_id: string | null;
  source_turn_id: string | null;
  source_message_id: string | null;
  tags: string[];
  created_at: string;
  updated_at: string;
  last_used_at: string | null;
  metadata: Record<string, unknown>;
};

export type DashboardMemories = {
  total: number;
  returned: number;
  memories: DashboardMemory[];
};

export type RuntimeSettings = {
  timezone: string;
  language: string;
  language_label: string;
  country_code: string;
  country_label: string;
  profile_id: string;
  user_display_name: string;
  privacy_scope: string;
  source: string;
  codex_test: boolean;
  database: {
    profile: string;
    codex_test: boolean;
    database_url: string;
    seed_database_url: string;
  };
  options: {
    languages: Array<{ code: string; label: string }>;
    timezones: Array<{ id: string; label: string }>;
    countries: Array<{ code: string; label: string }>;
    privacy_scopes: Array<{ id: string; label: string }>;
  };
};

export type UserProfile = {
  profile_id: string;
  display_name: string;
  language: string;
  language_label: string;
  country_code: string;
  country_label: string;
  timezone: string;
  privacy_scope: string;
  source: string;
  memory_count: number;
  top_memories: DashboardMemory[];
};

export type ApiError = {
  detail?: {
    code?: string;
    message?: string;
    recoverable?: boolean;
  };
};

export type HealthStatus = {
  status: string;
  app: string;
  environment: string;
  provider: string;
  model: string;
  database: {
    profile: string;
    codex_test: boolean;
    database_url: string;
    seed_database_url: string;
  };
};
