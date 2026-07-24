import type {
  ApiError,
  ChatMessage,
  ChatSession,
  ChatTurn,
  CognitiveEvent,
  DashboardMemories,
  HealthStatus,
  RuntimeSettings,
  ScarletStreamV2Event,
  StreamEvent,
  TraceItem,
  UserProfile
} from "./types";

const API_BASE_URL = normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL);

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(resolveApiPath(path), {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    ...init
  });

  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as ApiError;
      message = body.detail?.message || body.detail?.code || message;
    } catch {
      // Keep the HTTP status fallback.
    }
    throw new Error(message);
  }

  return (await response.json()) as T;
}

function resolveApiPath(path: string): string {
  if (/^https?:\/\//.test(path)) {
    return path;
  }
  return `${API_BASE_URL}${path}`;
}

function normalizeBaseUrl(value: unknown): string {
  if (typeof value !== "string" || !value.trim()) {
    return "";
  }
  return value.replace(/\/$/, "");
}

export function createSession(title?: string): Promise<ChatSession> {
  return request<ChatSession>("/api/chat/sessions", {
    method: "POST",
    body: JSON.stringify({
      title: title || null,
      metadata: { client: "frontend" }
    })
  });
}

export function fetchSessions(limit = 30): Promise<ChatSession[]> {
  return request<ChatSession[]>(`/api/chat/sessions?limit=${limit}`);
}

export function sendTurn(
  sessionId: string,
  message: string,
  maxTokens?: number
): Promise<ChatTurn> {
  return request<ChatTurn>(`/api/chat/sessions/${sessionId}/turn`, {
    method: "POST",
    body: JSON.stringify({
      message,
      max_tokens: maxTokens || null
    })
  });
}

export async function streamTurn(
  sessionId: string,
  message: string,
  maxTokens: number | undefined,
  onEvent: (event: StreamEvent) => void
): Promise<void> {
  const response = await fetch(resolveApiPath(`/api/chat/sessions/${sessionId}/turn/stream`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      max_tokens: maxTokens || null
    })
  });

  if (!response.ok) {
    let error = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as ApiError;
      error = body.detail?.message || body.detail?.code || error;
    } catch {
      // Keep the HTTP status fallback.
    }
    throw new Error(error);
  }

  if (!response.body) {
    throw new Error("Streaming response body is unavailable.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed) {
        onEvent(JSON.parse(trimmed) as StreamEvent);
      }
    }
  }

  const finalLine = buffer.trim();
  if (finalLine) {
    onEvent(JSON.parse(finalLine) as StreamEvent);
  }
}

export async function streamTurnV2(
  sessionId: string,
  message: string,
  maxTokens: number | undefined,
  onEvent: (event: ScarletStreamV2Event) => void
): Promise<string> {
  const initialResponse = await fetch(
    resolveApiPath(`/api/chat/sessions/${sessionId}/turn/stream-v2`),
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        max_tokens: maxTokens || null
      })
    }
  );
  await requireStreamingResponse(initialResponse);

  const turnId = initialResponse.headers.get("X-Scarlet-Turn-ID");
  if (!turnId) {
    throw new Error("The streaming response did not identify its turn.");
  }

  const state = {
    afterSeq: 0,
    terminal: false,
    seenEventIds: new Set<string>()
  };
  let lastStreamError: unknown = null;
  try {
    await consumeStreamV2(initialResponse, state, onEvent);
  } catch (error) {
    lastStreamError = error;
  }

  for (let attempt = 1; !state.terminal && attempt <= 5; attempt += 1) {
    await delay(250 * 2 ** (attempt - 1));
    try {
      const query = new URLSearchParams({ after_seq: String(state.afterSeq) });
      const response = await fetch(
        resolveApiPath(
          `/api/chat/sessions/${sessionId}/turns/${turnId}/stream-v2?${query}`
        )
      );
      await requireStreamingResponse(response);
      await consumeStreamV2(response, state, onEvent);
      lastStreamError = null;
    } catch (error) {
      lastStreamError = error;
    }
  }

  if (!state.terminal) {
    const detail =
      lastStreamError instanceof Error ? ` ${lastStreamError.message}` : "";
    throw new Error(
      `The Scarlet turn stream could not be resumed after 5 attempts.${detail}`
    );
  }
  return turnId;
}

async function requireStreamingResponse(response: Response): Promise<void> {
  if (!response.ok) {
    let error = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as ApiError;
      error = body.detail?.message || body.detail?.code || error;
    } catch {
      // Keep the HTTP status fallback.
    }
    throw new Error(error);
  }
  if (!response.body) {
    throw new Error("Streaming response body is unavailable.");
  }
}

async function consumeStreamV2(
  response: Response,
  state: {
    afterSeq: number;
    terminal: boolean;
    seenEventIds: Set<string>;
  },
  onEvent: (event: ScarletStreamV2Event) => void
): Promise<void> {
  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const applyLine = (line: string) => {
    const trimmed = line.trim();
    if (!trimmed) {
      return;
    }
    const event = JSON.parse(trimmed) as ScarletStreamV2Event;
    state.afterSeq = Math.max(state.afterSeq, event.seq);
    if (state.seenEventIds.has(event.event_id)) {
      return;
    }
    state.seenEventIds.add(event.event_id);
    state.terminal =
      event.event_type === "turn.completed" || event.event_type === "turn.failed";
    onEvent(event);
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    lines.forEach(applyLine);
  }
  applyLine(buffer);
}

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => globalThis.setTimeout(resolve, milliseconds));
}

export function fetchMessages(sessionId: string): Promise<ChatMessage[]> {
  return request<ChatMessage[]>(`/api/chat/sessions/${sessionId}/messages`);
}

export function fetchTraces(turnId: string): Promise<TraceItem[]> {
  return request<TraceItem[]>(`/api/debug/traces/${turnId}`);
}

export function fetchEvents(params: {
  sessionId?: string;
  turnId?: string;
  limit?: number;
}): Promise<CognitiveEvent[]> {
  const query = new URLSearchParams();
  if (params.sessionId) {
    query.set("session_id", params.sessionId);
  }
  if (params.turnId) {
    query.set("turn_id", params.turnId);
  }
  if (params.limit) {
    query.set("limit", String(params.limit));
  }
  return request<CognitiveEvent[]>(`/api/debug/events?${query.toString()}`);
}

export function fetchRuntimeSettings(): Promise<RuntimeSettings> {
  return request<RuntimeSettings>("/api/dashboard/settings");
}

export function updateRuntimeSettings(payload: {
  timezone?: string;
  language?: string;
  country_code?: string;
  profile_id?: string;
  user_display_name?: string;
  privacy_scope?: string;
}): Promise<RuntimeSettings> {
  return request<RuntimeSettings>("/api/dashboard/settings", {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function fetchDashboardMemories(params: {
  scope?: "user" | "project";
  limit?: number;
} = {}): Promise<DashboardMemories> {
  const query = new URLSearchParams();
  if (params.scope) {
    query.set("scope", params.scope);
  }
  if (params.limit) {
    query.set("limit", String(params.limit));
  }
  return request<DashboardMemories>(`/api/dashboard/memories?${query.toString()}`);
}

export function fetchUserProfile(): Promise<UserProfile> {
  return request<UserProfile>("/api/dashboard/profile");
}

export function fetchHealth(): Promise<HealthStatus> {
  return request<HealthStatus>("/health");
}
