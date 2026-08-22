import type {
  ApiError,
  AutonomyHistory,
  ChatMessage,
  ChatSession,
  ChatTurn,
  CognitiveEvent,
  DashboardResearchLab,
  DashboardMemories,
  DeviceExplorationSummary,
  DeviceObservationBatchResponse,
  DeviceObservationInput,
  DeviceObservationList,
  HealthStatus,
  RuntimeSettings,
  ScarletLiveFrame,
  ScarletLiveItem,
  ScarletStreamEvent,
  ScarletStreamReplay,
  StreamEvent,
  TraceItem,
  UserProfile,
  VideoCallState
} from "./types";

const API_BASE_URL = normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL);
let nativeBasicAuthorization: string | null = null;

export function setNativeApiBasicAuth(
  username: string,
  password: string
): void {
  nativeBasicAuthorization = `Basic ${window.btoa(`${username}:${password}`)}`;
}

export function clearNativeApiBasicAuth(): void {
  nativeBasicAuthorization = null;
}

function apiHeaders(headers?: HeadersInit): Headers {
  const resolved = new Headers(headers);
  resolved.set("Content-Type", "application/json");
  if (nativeBasicAuthorization) {
    resolved.set("Authorization", nativeBasicAuthorization);
  }
  return resolved;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(resolveApiPath(path), {
    ...init,
    headers: apiHeaders(init?.headers)
  });

  if (!response.ok) {
    throw await responseError(response);
  }

  return (await response.json()) as T;
}

async function responseError(response: Response): Promise<Error> {
  let message = `${response.status} ${response.statusText}`;
  try {
    const body = (await response.json()) as ApiError;
    message = body.detail?.message || body.detail?.code || message;
  } catch {
    // Keep the HTTP status fallback.
  }
  return new Error(message);
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

export function fetchAutonomyHistory(limit = 20): Promise<AutonomyHistory> {
  return request<AutonomyHistory>(`/api/autonomy/history?limit=${limit}`);
}

export function appendDeviceObservations(
  observations: DeviceObservationInput[]
): Promise<DeviceObservationBatchResponse> {
  return request<DeviceObservationBatchResponse>(
    "/api/device-exploration/observations/batch",
    {
      method: "POST",
      body: JSON.stringify({ observations })
    }
  );
}

export function fetchDeviceObservations(options?: {
  deviceId?: string;
  runId?: string;
  probe?: string;
  limit?: number;
}): Promise<DeviceObservationList> {
  const query = new URLSearchParams();
  if (options?.deviceId) query.set("device_id", options.deviceId);
  if (options?.runId) query.set("run_id", options.runId);
  if (options?.probe) query.set("probe", options.probe);
  query.set("limit", String(options?.limit ?? 200));
  return request<DeviceObservationList>(
    `/api/device-exploration/observations?${query}`
  );
}

export function fetchDeviceExplorationSummary(options?: {
  deviceId?: string;
  runId?: string;
}): Promise<DeviceExplorationSummary> {
  const query = new URLSearchParams();
  if (options?.deviceId) query.set("device_id", options.deviceId);
  if (options?.runId) query.set("run_id", options.runId);
  return request<DeviceExplorationSummary>(
    `/api/device-exploration/summary?${query}`
  );
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
    headers: apiHeaders(),
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
): Promise<string> {
  const initialResponse = await fetch(
    resolveApiPath(`/api/chat/sessions/${sessionId}/turn/stream-v2`),
    {
      method: "POST",
      headers: apiHeaders(),
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
        ),
        { headers: apiHeaders() }
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

export async function streamTurnLive(
  sessionId: string,
  message: string,
  maxTokens: number | undefined,
  onEvent: (event: ScarletStreamEvent) => void,
  onFrame: (frame: ScarletLiveFrame) => void
): Promise<string> {
  const initialResponse = await fetch(
    resolveApiPath(`/api/chat/sessions/${sessionId}/turn/stream-live`),
    {
      method: "POST",
      headers: apiHeaders(),
      body: JSON.stringify({
        message,
        max_tokens: maxTokens || null
      })
    }
  );
  await requireLiveStreamingResponse(initialResponse);

  return completeLiveTurnStream(
    initialResponse,
    sessionId,
    onEvent,
    onFrame
  );
}

export function startInteractiveVideoCall(
  sessionId: string
): Promise<VideoCallState> {
  return request<VideoCallState>("/api/perception/videocall/start", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, client: "android_app" })
  });
}

export function markVideoCallSpeechStarted(
  callId: string,
  utteranceId: string
): Promise<VideoCallState> {
  return request<VideoCallState>(
    `/api/perception/videocall/${callId}/speech-start`,
    {
      method: "POST",
      body: JSON.stringify({ utterance_id: utteranceId })
    }
  );
}

export function stopInteractiveVideoCall(
  callId: string
): Promise<VideoCallState> {
  return request<VideoCallState>(
    `/api/perception/videocall/${callId}/stop`,
    { method: "POST" }
  );
}

export async function streamInteractiveVideoCallTurn(
  callId: string,
  sessionId: string,
  utteranceId: string,
  transcript: string,
  onEvent: (event: ScarletStreamEvent) => void,
  onFrame: (frame: ScarletLiveFrame) => void
): Promise<string> {
  const initialResponse = await fetch(
    resolveApiPath(
      `/api/perception/videocall/${callId}/turn/stream-live`
    ),
    {
      method: "POST",
      headers: apiHeaders(),
      body: JSON.stringify({
        utterance_id: utteranceId,
        transcript
      })
    }
  );
  await requireLiveStreamingResponse(initialResponse);

  return completeLiveTurnStream(
    initialResponse,
    sessionId,
    onEvent,
    onFrame
  );
}

async function completeLiveTurnStream(
  initialResponse: Response,
  sessionId: string,
  onEvent: (event: ScarletStreamEvent) => void,
  onFrame: (frame: ScarletLiveFrame) => void
): Promise<string> {

  const turnId = initialResponse.headers.get("X-Scarlet-Turn-ID");
  if (!turnId) {
    throw new Error("The live response did not identify its turn.");
  }

  const state = {
    afterSeq: 0,
    terminal: false,
    seenEventIds: new Set<string>()
  };
  let lastStreamError: unknown = null;
  try {
    await consumeLiveStream(initialResponse, state, onEvent, onFrame);
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
        ),
        { headers: apiHeaders() }
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
      `The Scarlet live stream could not be resumed after 5 attempts.${detail}`
    );
  }
  return turnId;
}

async function requireLiveStreamingResponse(response: Response): Promise<void> {
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
    response.headers.get("X-Scarlet-Stream-Schema") !== "scarlet-live-v1"
  ) {
    throw new Error("Contratto live Scarlet non riconosciuto.");
  }
  if (!response.body) {
    throw new Error("Live streaming response body is unavailable.");
  }
}

async function consumeLiveStream(
  response: Response,
  state: {
    afterSeq: number;
    terminal: boolean;
    seenEventIds: Set<string>;
  },
  onEvent: (event: ScarletStreamEvent) => void,
  onFrame: (frame: ScarletLiveFrame) => void
): Promise<void> {
  await consumeNdjson(response, (line) => {
    const item = JSON.parse(line) as ScarletLiveItem;
    if (item.schema_version !== "scarlet-live-v1") {
      throw new Error("Elemento live Scarlet non valido.");
    }
    if (item.kind === "frame") {
      onFrame(item.frame);
      return;
    }
    applyStreamV2Event(item.event, state, onEvent);
  });
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
  if (
    response.headers.get("X-Scarlet-Stream-Schema") !== "scarlet-stream-v2"
  ) {
    throw new Error("Contratto stream Scarlet V2 non riconosciuto.");
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
  onEvent: (event: ScarletStreamEvent) => void
): Promise<void> {
  await consumeNdjson(response, (line) => {
    const event = JSON.parse(line) as ScarletStreamEvent;
    if (event.schema_version !== "scarlet-stream-v2") {
      throw new Error("Evento stream Scarlet V2 non valido.");
    }
    applyStreamV2Event(event, state, onEvent);
  });
}

async function consumeNdjson(
  response: Response,
  onLine: (line: string) => void
): Promise<void> {
  const reader = response.body!.getReader();
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
      if (trimmed) onLine(trimmed);
    }
  }
  const trimmed = buffer.trim();
  if (trimmed) onLine(trimmed);
}

function applyStreamV2Event(
  event: ScarletStreamEvent,
  state: {
    afterSeq: number;
    terminal: boolean;
    seenEventIds: Set<string>;
  },
  onEvent: (event: ScarletStreamEvent) => void
): void {
  state.afterSeq = Math.max(state.afterSeq, event.seq);
  if (state.seenEventIds.has(event.event_id)) {
    return;
  }
  state.seenEventIds.add(event.event_id);
  state.terminal =
    event.event_type === "turn.completed" || event.event_type === "turn.failed";
  onEvent(event);
}

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => globalThis.setTimeout(resolve, milliseconds));
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

export function fetchDashboardResearchLab(): Promise<DashboardResearchLab> {
  return request<DashboardResearchLab>("/api/dashboard/research-lab");
}

export async function fetchResearchLabArtifactContent(artifactId: string): Promise<Blob> {
  const response = await fetch(
    resolveApiPath(`/api/dashboard/research-lab/artifacts/${artifactId}/content`),
    { headers: apiHeaders() }
  );
  if (!response.ok) {
    throw await responseError(response);
  }
  return response.blob();
}

export async function deleteResearchLabArtifact(artifactId: string): Promise<void> {
  const response = await fetch(
    resolveApiPath(`/api/dashboard/research-lab/artifacts/${artifactId}`),
    { method: "DELETE", headers: apiHeaders() }
  );
  if (!response.ok) {
    throw await responseError(response);
  }
}

export function fetchUserProfile(): Promise<UserProfile> {
  return request<UserProfile>("/api/dashboard/profile");
}

export function fetchHealth(): Promise<HealthStatus> {
  return request<HealthStatus>("/health");
}
