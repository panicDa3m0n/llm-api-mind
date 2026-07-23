import type {
  ApiError,
  ChatMessage,
  ChatSession,
  ChatTurn,
  CognitiveEvent,
  DashboardMemories,
  HealthStatus,
  RuntimeSettings,
  ScarletStreamEvent,
  ScarletStreamReplay,
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
  onEvent: (event: ScarletStreamEvent) => void
): Promise<void> {
  const response = await fetch(
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

  if (
    response.headers.get("X-Scarlet-Stream-Schema") !== "scarlet-stream-v2"
  ) {
    throw new Error("Contratto stream Scarlet V2 non riconosciuto.");
  }
  if (!response.body) {
    throw new Error("Streaming response body is unavailable.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  function emitLine(line: string) {
    const trimmed = line.trim();
    if (!trimmed) return;
    const event = JSON.parse(trimmed) as ScarletStreamEvent;
    if (event.schema_version !== "scarlet-stream-v2") {
      throw new Error("Evento stream Scarlet V2 non valido.");
    }
    onEvent(event);
  }

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    lines.forEach(emitLine);
  }
  emitLine(buffer);
}

export function fetchSessionEventsV2(
  sessionId: string,
  afterSeq = 0,
  limit = 500
): Promise<ScarletStreamReplay> {
  const query = new URLSearchParams({
    after_seq: String(afterSeq),
    limit: String(limit)
  });
  return request<ScarletStreamReplay>(
    `/api/chat/sessions/${sessionId}/events?${query.toString()}`
  );
}

export async function fetchAllSessionEventsV2(
  sessionId: string
): Promise<ScarletStreamEvent[]> {
  const eventsById = new Map<string, ScarletStreamEvent>();
  let afterSeq = 0;

  for (let pageNumber = 0; pageNumber < 100; pageNumber += 1) {
    const page = await fetchSessionEventsV2(sessionId, afterSeq, 500);
    for (const event of page.events) {
      if (
        event.schema_version !== "scarlet-stream-v2" ||
        event.session_id !== sessionId ||
        !Number.isInteger(event.seq) ||
        event.seq < 1
      ) {
        throw new Error("Envelope replay Scarlet V2 non valido.");
      }
      const existing = eventsById.get(event.event_id);
      if (existing && JSON.stringify(existing) !== JSON.stringify(event)) {
        throw new Error(`Conflitto evento replay: ${event.event_id}`);
      }
      eventsById.set(event.event_id, event);
    }
    if (!page.cursor.has_more) {
      const events = [...eventsById.values()].sort(
        (left, right) =>
          left.seq - right.seq || left.event_id.localeCompare(right.event_id)
      );
      let expectedSeq = 1;
      for (const event of events) {
        if (event.seq !== expectedSeq) {
          throw new Error(
            `Gap nel replay Scarlet V2: atteso ${expectedSeq}, ricevuto ${event.seq}.`
          );
        }
        expectedSeq += 1;
      }
      if (page.cursor.latest_seq !== events.length) {
        throw new Error("Cursore replay Scarlet V2 non coerente.");
      }
      return events;
    }
    if (page.cursor.next_after_seq <= afterSeq) {
      throw new Error("Il cursore replay Scarlet non avanza.");
    }
    afterSeq = page.cursor.next_after_seq;
  }

  throw new Error("Replay Scarlet oltre il limite di sicurezza.");
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
