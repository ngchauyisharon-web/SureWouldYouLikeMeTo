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
  choices: string[];
  static_line?: string | null;
};

export type StatePatch = {
  neural_score: number;
  turn_index: number;
  choices?: string[];
  static_line?: string | null;
  ended?: boolean;
  achievement_unlocked?: string | null;
};

function apiPrefix(): string {
  try {
    return globalThis.localStorage.getItem("sure_api_base")?.trim() ?? "";
  } catch {
    return "";
  }
}

export async function fetchScenarios(): Promise<ScenarioSummary[]> {
  const res = await fetch(`${apiPrefix()}/api/scenarios`);
  if (!res.ok) throw new Error("failed_scenarios");
  const data = (await res.json()) as { scenarios: ScenarioSummary[] };
  return data.scenarios;
}

export async function createSession(slug: string): Promise<SessionSnapshot> {
  const res = await fetch(`${apiPrefix()}/api/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario_slug: slug }),
  });
  if (!res.ok) throw new Error("failed_session");
  return res.json() as Promise<SessionSnapshot>;
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
    onDone: () => void;
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
          handlers.onStatePatch(payload as unknown as StatePatch);
        } else if (eventName === "done") {
          handlers.onDone();
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
