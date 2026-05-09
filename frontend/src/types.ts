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

export type StreamEvent = {
  type: string;
  data: Record<string, unknown>;
};

export type AgentStep = {
  id: string;
  kind: "thinking" | "tool" | "result" | "answer" | "runtime";
  title: string;
  body: string;
  status: "active" | "done" | "error";
};

export type ApiError = {
  detail?: {
    code?: string;
    message?: string;
    recoverable?: boolean;
  };
};
