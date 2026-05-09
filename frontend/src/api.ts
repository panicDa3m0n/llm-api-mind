import type {
  ApiError,
  ChatMessage,
  ChatSession,
  ChatTurn,
  StreamEvent,
  TraceItem
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
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

export function createSession(title?: string): Promise<ChatSession> {
  return request<ChatSession>("/api/chat/sessions", {
    method: "POST",
    body: JSON.stringify({
      title: title || null,
      metadata: { client: "frontend" }
    })
  });
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
  const response = await fetch(`/api/chat/sessions/${sessionId}/turn/stream`, {
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

export function fetchMessages(sessionId: string): Promise<ChatMessage[]> {
  return request<ChatMessage[]>(`/api/chat/sessions/${sessionId}/messages`);
}

export function fetchTraces(turnId: string): Promise<TraceItem[]> {
  return request<TraceItem[]>(`/api/debug/traces/${turnId}`);
}

export function fetchHealth(): Promise<{ status: string; app: string; model: string }> {
  return request<{ status: string; app: string; model: string }>("/health");
}
