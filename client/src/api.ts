export type ScenarioSummary = {
  slug: string;
  title: string;
  icon: string;
  tagline: string;
  body: string;
};

export type SessionSnapshot = {
  session_id: string;
  scenario: ScenarioSummary;
  phase: string;
  turn_index: number;
  neural_score: number;
  answer_mode?: "free_text" | "ai_options" | null;
  choices: string[];
  static_line?: string | null;
  scenario_art_status?: string;
  scenario_art_b64?: string | null;
  scenario_art_detail?: string | null;
  scenario_art_turn_index?: number | null;
  scenario_mode?: "static" | "dynamic";
  outline_generation_error?: string | null;
  turn_generation_error?: string | null;
};

export type AnswerModeResponse = {
  phase: string;
  answer_mode: "free_text" | "ai_options";
  neural_score: number;
  turn_index: number;
  choices: string[];
  static_line?: string | null;
  ai_options_penalty?: number;
  scenario_art_status?: string;
  scenario_art_b64?: string | null;
  scenario_art_detail?: string | null;
  scenario_art_turn_index?: number | null;
  choices_error?: string | null;
};

export type StatePatch = {
  neural_score: number;
  turn_index: number;
  choices?: string[];
  static_line?: string | null;
  ended?: boolean;
  achievement_unlocked?: string | null;
  scenario_art_status?: string;
  scenario_art_b64?: string | null;
  scenario_art_detail?: string | null;
  scenario_art_turn_index?: number | null;
  choices_error?: string | null;
  outcome_image_status?: string;
};

function apiPrefix(): string {
  try {
    const fromStorage = globalThis.localStorage.getItem("sure_api_base")?.trim();
    if (fromStorage) return fromStorage;
  } catch {
    /* ignore */
  }
  const fromEnv = (import.meta.env.VITE_API_BASE as string | undefined)?.trim();
  return fromEnv ?? "";
}

export async function fetchScenarios(): Promise<ScenarioSummary[]> {
  const res = await fetch(`${apiPrefix()}/api/scenarios`);
  if (!res.ok) throw new Error("failed_scenarios");
  const data = (await res.json()) as { scenarios: ScenarioSummary[] };
  return data.scenarios;
}

export async function createSession(
  slug: string,
  opts?: { generated?: boolean },
): Promise<SessionSnapshot> {
  const res = await fetch(`${apiPrefix()}/api/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      scenario_slug: slug,
      source: opts?.generated ? "generated" : "static",
    }),
  });
  if (!res.ok) throw new Error("failed_session");
  return res.json() as Promise<SessionSnapshot>;
}

export async function submitAnswerMode(
  sessionId: string,
  mode: "free_text" | "ai_options",
): Promise<AnswerModeResponse> {
  const res = await fetch(`${apiPrefix()}/api/sessions/${sessionId}/answer-mode`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode }),
  });
  if (!res.ok) throw new Error("failed_answer_mode");
  return res.json() as Promise<AnswerModeResponse>;
}

export async function submitFreeText(sessionId: string, text: string): Promise<void> {
  const res = await fetch(`${apiPrefix()}/api/sessions/${sessionId}/free-text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error("failed_free_text");
}

export async function submitChoice(sessionId: string, choiceIndex: number): Promise<void> {
  const res = await fetch(`${apiPrefix()}/api/sessions/${sessionId}/choice`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ choice_index: choiceIndex }),
  });
  if (!res.ok) throw new Error("failed_choice");
}

export async function consumeSessionStream(
  sessionId: string,
  handlers: {
    onToken: (t: string) => void;
    onStatePatch: (p: StatePatch) => void;
    /** Includes the last `state_patch` payload from this stream so callers can read `ended` reliably. */
    onDone: (lastPatch?: StatePatch) => void;
    onError: (msg: string) => void;
  },
): Promise<void> {
  const res = await fetch(`${apiPrefix()}/api/sessions/${sessionId}/stream`);
  if (!res.ok || !res.body) {
    handlers.onError("stream_http_error");
    return;
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let lastStatePatch: StatePatch | undefined;

  const parseBlocks = (text: string) => {
    const blocks = text.split("\n\n");
    const rest = blocks.pop() ?? "";
    for (const block of blocks) {
      let eventName = "message";
      let dataLine = "";
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) eventName = line.slice(6).trim();
        if (line.startsWith("data:")) dataLine = line.slice(5).trim();
      }
      if (!dataLine) continue;
      try {
        const payload = JSON.parse(dataLine) as Record<string, unknown>;
        if (eventName === "token" && typeof payload.t === "string") {
          handlers.onToken(payload.t);
        } else if (eventName === "state_patch") {
          lastStatePatch = payload as unknown as StatePatch;
          handlers.onStatePatch(lastStatePatch);
        } else if (eventName === "done") {
          handlers.onDone(lastStatePatch);
        } else if (eventName === "error") {
          handlers.onError(String(payload.message ?? "error"));
        }
      } catch {
        handlers.onError("parse_error");
      }
    }
    return rest;
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    buffer = parseBlocks(buffer);
  }
  if (buffer.trim()) {
    parseBlocks(buffer + "\n\n");
  }
}

export async function neurobotChat(
  sessionId: string,
  message: string,
): Promise<{ reply: string; neural_score: number }> {
  const res = await fetch(`${apiPrefix()}/api/sessions/${sessionId}/neurobot-chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) throw new Error("failed_neurobot");
  return res.json() as Promise<{ reply: string; neural_score: number }>;
}

export async function fetchScenarioArt(sessionId: string): Promise<{
  status: string;
  b64: string | null;
  detail?: string | null;
  scenario_art_turn_index?: number | null;
}> {
  const res = await fetch(`${apiPrefix()}/api/sessions/${sessionId}/scenario-art`);
  if (!res.ok) throw new Error("failed_scenario_art");
  return res.json() as Promise<{
    status: string;
    b64: string | null;
    detail?: string | null;
    scenario_art_turn_index?: number | null;
  }>;
}

export async function fetchOutcomeImage(sessionId: string): Promise<{
  status: string;
  b64: string | null;
  detail?: string | null;
}> {
  const res = await fetch(`${apiPrefix()}/api/sessions/${sessionId}/outcome-image`);
  if (!res.ok) throw new Error("failed_outcome_image");
  return res.json() as Promise<{
    status: string;
    b64: string | null;
    detail?: string | null;
  }>;
}
