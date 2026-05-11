import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import {
  consumeSessionStream,
  createSession,
  fetchOutcomeImage,
  fetchScenarioArt,
  neurobotChat,
  submitAnswerMode,
  submitChoice,
  submitFreeText,
  type AnswerModeResponse,
  type SessionSnapshot,
  type StatePatch,
} from "./api";
import { publicUrl } from "./publicUrl";
import { theme } from "./theme";

const ARCHIVE_KEY = "sure_archives_v1";

/** Hero art per scenario slug (topic card assets). */
const SCENARIO_HERO_ART: Record<string, string> = {
  ai_overuse: "topics/ai-overuse.png",
  hallucination: "topics/hallucination.png",
  ethics: "topics/ethics.png",
};

/** Visual variants for AI option cards (cycles by choice index). */
const PATH_VARIANTS = [
  {
    tone: "hard" as const,
    pathLabel: "THE HARD PATH",
    cta: "EXECUTE COMMAND →",
    icon: "!",
  },
  {
    tone: "easy" as const,
    pathLabel: "THE EASY PATH",
    cta: "APPROVE AUTOMATION →",
    icon: "🚀",
  },
  {
    tone: "lazy" as const,
    pathLabel: "THE LAZY PATH",
    cta: "INITIATE LOOP →",
    icon: "🪄",
  },
  {
    tone: "chaos" as const,
    pathLabel: "THE CHAOS PATH",
    cta: "RESET REALITY →",
    icon: "🗑️",
  },
];

function stripScoreLine(text: string): string {
  return text.replace(/\r?\nSCORE_CHANGE:\s*[+-]?\d+\s*$/i, "").trim();
}

type ScenarioPolaroidGenerationPhase = "static" | "loading" | "ready" | "failed";

function ScenarioHeroBanner({
  snap,
  staticLine,
  footNote,
  enlarge,
  polaroidSrc,
  polaroidGenerationPhase,
  polaroidFailDetail,
}: {
  snap: SessionSnapshot;
  staticLine: string | null;
  footNote: string;
  polaroidSrc: string;
  polaroidGenerationPhase: ScenarioPolaroidGenerationPhase;
  polaroidFailDetail?: string | null;
  /** +50% scale for the answer-mode choice screen only */
  enlarge?: boolean;
}) {
  const polaroidCaption =
    polaroidGenerationPhase === "loading"
      ? "Generating scene for this dilemma…"
      : polaroidGenerationPhase === "ready"
        ? "AI-generated scene for this dilemma"
        : polaroidGenerationPhase === "failed"
          ? "Illustration unavailable (offline API or generation skipped)."
          : null;

  return (
    <div
      className={`ai-scenario-hero${enlarge ? " ai-scenario-hero--enlarged" : ""}`}
      aria-label="Scenario briefing"
    >
      <div className="ai-scenario-hero-text">
        <span className="ai-scenario-pill">URGENT DILEMMA</span>
        <p className="ai-scenario-num">SCENARIO {String(snap.turn_index + 1).padStart(3, "0")}:</p>
        <h2 className="ai-scenario-title">{snap.scenario.title.toUpperCase()}</h2>
        <p className="ai-scenario-desc">
          {staticLine ?? snap.scenario.tagline}{" "}
          <span className="ai-scenario-body-extra">{snap.scenario.body}</span>
        </p>
        <span className="ai-scenario-footpill">{footNote}</span>
      </div>
      <div className="ai-scenario-polaroid">
        <div className="ai-scenario-polaroid-frame">
          <img src={polaroidSrc} alt="" className="ai-scenario-polaroid-img" />
          {polaroidGenerationPhase === "loading" ? (
            <div className="ai-scenario-polaroid-overlay" aria-live="polite" aria-busy="true">
              <span className="ai-scenario-polaroid-spinner" aria-hidden />
            </div>
          ) : null}
        </div>
        {polaroidCaption ? (
          <span className="ai-scenario-polaroid-caption-wrap">
            <span
              className={`ai-scenario-polaroid-caption${polaroidGenerationPhase === "failed" ? " ai-scenario-polaroid-caption--fallback" : ""}`}
            >
              {polaroidCaption}
            </span>
            {polaroidGenerationPhase === "failed" && polaroidFailDetail?.trim() ? (
              <span className="ai-scenario-polaroid-detail">{polaroidFailDetail.trim()}</span>
            ) : null}
          </span>
        ) : null}
      </div>
    </div>
  );
}

function pushArchive(entry: {
  slug: string;
  title: string;
  score: number;
  achievement?: string | null;
  at?: string;
}) {
  try {
    const raw = globalThis.localStorage.getItem(ARCHIVE_KEY);
    const prev = raw ? (JSON.parse(raw) as typeof entry[]) : [];
    prev.unshift({ ...entry, at: new Date().toISOString() });
    globalThis.localStorage.setItem(ARCHIVE_KEY, JSON.stringify(prev.slice(0, 50)));
  } catch {
    /* ignore */
  }
}

export function Play() {
  const { slug } = useParams<{ slug: string }>();
  const [searchParams] = useSearchParams();
  const aiGeneratedRun = searchParams.get("generated") === "1";
  const [snap, setSnap] = useState<SessionSnapshot | null>(null);
  const [sessionBooting, setSessionBooting] = useState(false);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const [streamErr, setStreamErr] = useState<string | null>(null);
  const [modeErr, setModeErr] = useState<string | null>(null);
  const [narrative, setNarrative] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [choices, setChoices] = useState<string[]>([]);
  const [staticLine, setStaticLine] = useState<string | null>(null);
  const [ended, setEnded] = useState(false);
  const [achievement, setAchievement] = useState<string | null>(null);
  const [score, setScore] = useState(50);
  const [freeDraft, setFreeDraft] = useState("");
  const [neuroMessages, setNeuroMessages] = useState<{ role: "user" | "assistant"; text: string }[]>([]);
  const [neuroAsk, setNeuroAsk] = useState("");
  const [neuroSending, setNeuroSending] = useState(false);
  const [scenarioHeroB64, setScenarioHeroB64] = useState<string | null>(null);
  const [scenarioHeroArtPhase, setScenarioHeroArtPhase] = useState<ScenarioPolaroidGenerationPhase>("static");
  const [scenarioArtFailDetail, setScenarioArtFailDetail] = useState<string | null>(null);
  const [outcomePhase, setOutcomePhase] = useState<"hidden" | "loading" | "ready" | "failed">("hidden");
  const [outcomeB64, setOutcomeB64] = useState<string | null>(null);

  const snapRef = useRef<SessionSnapshot | null>(null);
  snapRef.current = snap;

  useEffect(() => {
    setScenarioHeroB64(null);
    setScenarioHeroArtPhase("static");
    setScenarioArtFailDetail(null);
    setOutcomePhase("hidden");
    setOutcomeB64(null);
  }, [slug]);

  useEffect(() => {
    if (!slug) return;
    setSnap(null);
    setLoadErr(null);
    setSessionBooting(true);
    createSession(slug, { generated: aiGeneratedRun })
      .then((s) => {
        setSnap(s);
        setChoices(s.choices);
        setStaticLine(s.static_line ?? null);
        setScore(s.neural_score);
        const artSt = s.scenario_art_status ?? "idle";
        if (artSt === "ready" && s.scenario_art_b64) {
          setScenarioHeroB64(s.scenario_art_b64);
          setScenarioHeroArtPhase("ready");
          setScenarioArtFailDetail(null);
        } else if (artSt === "pending") {
          setScenarioHeroArtPhase("loading");
          setScenarioArtFailDetail(null);
        } else if (artSt === "failed") {
          setScenarioHeroArtPhase("failed");
          setScenarioArtFailDetail(s.scenario_art_detail ?? null);
        } else {
          setScenarioHeroArtPhase("static");
          setScenarioArtFailDetail(null);
        }
      })
      .catch(() => setLoadErr("Could not start session."))
      .finally(() => setSessionBooting(false));
  }, [slug, aiGeneratedRun]);

  useEffect(() => {
    if (!snap) return;
    const status = snap.scenario_art_status ?? "idle";

    if (status === "ready" && snap.scenario_art_b64) {
      setScenarioHeroB64(snap.scenario_art_b64);
      setScenarioHeroArtPhase("ready");
      setScenarioArtFailDetail(null);
      return;
    }

    if (status === "idle") {
      setScenarioHeroArtPhase("static");
      setScenarioArtFailDetail(null);
      return;
    }

    if (status === "failed") {
      setScenarioHeroArtPhase("failed");
      setScenarioArtFailDetail(snap.scenario_art_detail ?? null);
      return;
    }

    if (status !== "pending") {
      setScenarioHeroArtPhase("static");
      setScenarioArtFailDetail(null);
      return;
    }

    setScenarioHeroArtPhase("loading");
    setScenarioArtFailDetail(null);
    let cancelled = false;
    void (async () => {
      let fetchErrors = 0;
      for (let i = 0; i < 90; i++) {
        try {
          const r = await fetchScenarioArt(snap.session_id);
          fetchErrors = 0;
          if (cancelled) return;
          if (r.status === "ready" && r.b64) {
            setScenarioHeroB64(r.b64);
            setScenarioHeroArtPhase("ready");
            setScenarioArtFailDetail(null);
            return;
          }
          if (r.status === "failed") {
            setScenarioHeroArtPhase("failed");
            setScenarioArtFailDetail(r.detail?.trim() || null);
            return;
          }
          if (r.status === "idle") {
            setScenarioHeroArtPhase("static");
            setScenarioArtFailDetail(null);
            return;
          }
        } catch {
          fetchErrors++;
          if (fetchErrors >= 8) {
            if (!cancelled) {
              setScenarioHeroArtPhase("failed");
              setScenarioArtFailDetail(null);
            }
            return;
          }
        }
        await new Promise((x) => setTimeout(x, 2000));
      }
      if (!cancelled) {
        setScenarioHeroArtPhase("failed");
        setScenarioArtFailDetail(null);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [snap?.session_id, snap?.scenario_art_status, snap?.turn_index]);

  useEffect(() => {
    setNeuroMessages([]);
    setNeuroAsk("");
  }, [snap?.turn_index, snap?.answer_mode]);

  const mergeFromAnswerMode = useCallback((patch: AnswerModeResponse) => {
    setSnap((prev) =>
      prev
        ? {
            ...prev,
            phase: patch.phase,
            answer_mode: patch.answer_mode,
            neural_score: patch.neural_score,
            turn_index: patch.turn_index,
            choices: patch.choices,
            static_line: patch.static_line ?? prev.static_line,
            ...(patch.scenario_art_status !== undefined
              ? {
                  scenario_art_status: patch.scenario_art_status,
                  scenario_art_b64:
                    patch.scenario_art_b64 !== undefined ? patch.scenario_art_b64 : prev.scenario_art_b64,
                  scenario_art_detail:
                    patch.scenario_art_detail !== undefined ? patch.scenario_art_detail : prev.scenario_art_detail,
                  scenario_art_turn_index:
                    patch.scenario_art_turn_index !== undefined
                      ? patch.scenario_art_turn_index
                      : prev.scenario_art_turn_index,
                }
              : {}),
            turn_generation_error:
              patch.choices_error !== undefined
                ? patch.choices_error
                : patch.choices.length > 0
                  ? null
                  : prev.turn_generation_error,
          }
        : null,
    );
    setChoices(patch.choices);
    setStaticLine(patch.static_line ?? null);
    setScore(patch.neural_score);
    if (patch.choices_error && patch.choices.length === 0) {
      setModeErr(patch.choices_error);
    } else {
      setModeErr(null);
    }
  }, []);

  const pollOutcomeFor = useCallback(async (sessionId: string) => {
    setOutcomePhase("loading");
    setOutcomeB64(null);
    let fetchErrors = 0;
    for (let i = 0; i < 90; i++) {
      try {
        const r = await fetchOutcomeImage(sessionId);
        fetchErrors = 0;
        if (r.status === "ready" && r.b64) {
          setOutcomeB64(r.b64);
          setOutcomePhase("ready");
          return;
        }
        if (r.status === "failed") {
          setOutcomePhase("failed");
          return;
        }
        if (r.status === "idle") {
          setOutcomePhase("hidden");
          setOutcomeB64(null);
          return;
        }
      } catch {
        fetchErrors++;
        if (fetchErrors >= 8) {
          setOutcomePhase("failed");
          return;
        }
      }
      await new Promise((x) => setTimeout(x, 2000));
    }
    setOutcomePhase("failed");
  }, []);

  const runStream = useCallback(async () => {
    const cur = snapRef.current;
    if (!cur) return;
    setStreaming(true);
    setStreamErr(null);
    setNarrative("");
    setNeuroMessages([]);
    try {
      await consumeSessionStream(cur.session_id, {
        onToken: (t) => setNarrative((prev) => prev + t),
        onStatePatch: (p: StatePatch) => {
          setScore(p.neural_score);
          setSnap((prev) =>
            prev
              ? {
                  ...prev,
                  neural_score: p.neural_score,
                  turn_index: p.turn_index,
                  phase: p.ended ? "ended" : prev.phase,
                  ...(p.scenario_art_status !== undefined
                    ? {
                        scenario_art_status: p.scenario_art_status,
                        scenario_art_b64:
                          p.scenario_art_b64 !== undefined ? p.scenario_art_b64 : prev.scenario_art_b64,
                        scenario_art_detail:
                          p.scenario_art_detail !== undefined ? p.scenario_art_detail : prev.scenario_art_detail,
                        scenario_art_turn_index:
                          p.scenario_art_turn_index !== undefined
                            ? p.scenario_art_turn_index
                            : prev.scenario_art_turn_index,
                      }
                    : {}),
                  turn_generation_error:
                    p.choices_error !== undefined
                      ? p.choices_error
                      : p.choices !== undefined && p.choices.length > 0
                        ? null
                        : prev.turn_generation_error,
                }
              : null,
          );
          if (p.choices !== undefined) setChoices(p.choices);
          if ("static_line" in p) setStaticLine(p.static_line ?? null);
          if (p.achievement_unlocked) setAchievement(p.achievement_unlocked);
          if (p.ended) {
            setEnded(true);
            const slugNow = snapRef.current?.scenario.slug;
            const titleNow = snapRef.current?.scenario.title;
            if (slugNow && titleNow) {
              pushArchive({
                slug: slugNow,
                title: titleNow,
                score: p.neural_score,
                achievement: p.achievement_unlocked ?? null,
              });
            }
          }
        },
        onDone: (lastPatch) => {
          setNarrative((prev) => stripScoreLine(prev));
          setStreaming(false);
          const sid = snapRef.current?.session_id;
          if (sid && lastPatch?.ended) void pollOutcomeFor(sid);
        },
        onError: (msg) => {
          setStreamErr(msg);
          setStreaming(false);
        },
      });
    } catch {
      setStreamErr("stream_failed");
      setStreaming(false);
    }
  }, [pollOutcomeFor]);

  const sendNeuroInvestigate = async () => {
    const q = neuroAsk.trim();
    const cur = snapRef.current;
    if (!cur || !q || neuroSending || streaming || ended) return;
    setNeuroSending(true);
    try {
      const r = await neurobotChat(cur.session_id, q);
      setNeuroMessages((prev) => [...prev, { role: "user", text: q }, { role: "assistant", text: r.reply }]);
      setNeuroAsk("");
      setScore(r.neural_score);
      setSnap((prev) => (prev ? { ...prev, neural_score: r.neural_score } : null));
    } catch {
      setStreamErr("neurobot_chat_failed");
    } finally {
      setNeuroSending(false);
    }
  };

  const pickAnswerMode = async (mode: "free_text" | "ai_options") => {
    if (!snap || streaming) return;
    setModeErr(null);
    try {
      const patch = await submitAnswerMode(snap.session_id, mode);
      mergeFromAnswerMode(patch);
    } catch {
      setModeErr("Could not set play style.");
    }
  };

  const onPick = async (idx: number) => {
    if (!snap || streaming || ended) return;
    try {
      await submitChoice(snap.session_id, idx);
      await runStream();
    } catch {
      setStreamErr("choice_failed");
    }
  };

  const onSubmitFreeText = async () => {
    const t = freeDraft.trim();
    if (!snap || !t || streaming || ended) return;
    try {
      await submitFreeText(snap.session_id, t);
      setFreeDraft("");
      await runStream();
    } catch {
      setStreamErr("free_text_failed");
    }
  };

  if (loadErr) {
    return (
      <div className="play-shell">
        <p>{loadErr}</p>
        <Link to="/">Back</Link>
      </div>
    );
  }

  if (!snap) {
    return (
      <div className="play-shell">
        <p>{sessionBooting ? (aiGeneratedRun ? "Generating scenario…" : "Loading…") : "Loading…"}</p>
      </div>
    );
  }

  const awaitingMode = snap.phase === "awaiting_answer_mode";
  const awaitingMc =
    snap.phase === "awaiting_choice" && snap.answer_mode === "ai_options" && choices.length > 0;
  const awaitingFree = snap.phase === "awaiting_choice" && snap.answer_mode === "free_text";

  /** No narrative yet on free-text flow — skip empty dialogue shell (hint is plain text outside). */
  const freeTextAwaitingEmpty =
    awaitingFree &&
    !narrative &&
    !streaming &&
    !ended &&
    !achievement &&
    outcomePhase === "hidden" &&
    !streamErr;

  /** Dock NeuroBot chat on the right whenever the player has picked a play style and the run is ongoing. */
  const showNeuroDock =
    (snap.answer_mode === "free_text" || snap.answer_mode === "ai_options") &&
    snap.phase !== "awaiting_answer_mode" &&
    !ended;

  const showScenarioHero = awaitingMode || awaitingMc || awaitingFree;
  const showStreamArea = !(
    !narrative &&
    !streaming &&
    !ended &&
    (awaitingMode || awaitingMc || freeTextAwaitingEmpty)
  );
  const showDialogue =
    !!achievement || !!(staticLine && !showScenarioHero) || showStreamArea || !!streamErr;

  const neuroDockPlaceholder =
    snap.answer_mode === "ai_options" && snap.phase === "awaiting_choice"
      ? "Ask before you choose…"
      : "What should you watch out for?";

  const polaroidFallback = publicUrl(SCENARIO_HERO_ART[snap.scenario.slug] ?? "landing-hero.png");
  const polaroidDataSrc =
    scenarioHeroArtPhase === "ready" && scenarioHeroB64 != null
      ? `data:image/png;base64,${scenarioHeroB64}`
      : polaroidFallback;

  const heroBanner = showScenarioHero ? (
    <ScenarioHeroBanner
      snap={snap}
      staticLine={staticLine}
      enlarge={awaitingMode}
      polaroidSrc={polaroidDataSrc}
      polaroidGenerationPhase={scenarioHeroArtPhase}
      polaroidFailDetail={scenarioArtFailDetail}
      footNote={
        awaitingMc
          ? "AI-suggested paths engaged"
          : awaitingFree
            ? "NeuroBot is listening — send your answer below"
            : "Choose NeuroBot or AI-suggested paths below"
      }
    />
  ) : null;

  const aiOptionsStage = awaitingMc ? (
    <section className="ai-options-stage" aria-label="Scenario choices">
      {!streaming && !ended ? (
        <p className="ai-options-hint">Pick a move — the narrator reacts in real time.</p>
      ) : null}
      <div className="ai-choice-grid">
        {choices.map((choiceText, i) => {
          const v = PATH_VARIANTS[i % PATH_VARIANTS.length];
          return (
            <button
              key={`${i}-${choiceText}`}
              type="button"
              className={`ai-path-card ai-path-card--${v.tone}`}
              disabled={streaming || ended}
              onClick={() => void onPick(i)}
            >
              <span className="ai-path-card-top">
                <span className="ai-path-icon" aria-hidden>
                  {v.icon}
                </span>
                <span className="ai-path-badge">{v.pathLabel}</span>
              </span>
              <span className="ai-path-title">{choiceText}</span>
              <span className="ai-path-desc">{snap.scenario.tagline}</span>
              <span className="ai-path-cta">{v.cta}</span>
            </button>
          );
        })}
      </div>
    </section>
  ) : null;

  const dialogueBody = (
    <>
      {achievement ? (
        <div className="achievement">
          Achievement unlocked: <strong>{achievement}</strong>
        </div>
      ) : null}
      {staticLine && !showScenarioHero ? (
        <p className="static-line">
          <em>{staticLine}</em>
        </p>
      ) : null}
      {showStreamArea ? (
        <div className="stream-box">
          {narrative || (streaming ? <span className="cursor">▍</span> : null)}
          {ended ? <p className="fin">Run complete. Your conscience may require a reboot.</p> : null}
        </div>
      ) : null}
      {outcomePhase === "loading" ? <p className="outcome-loading">Generating outcome illustration…</p> : null}
      {outcomePhase === "ready" && outcomeB64 ? (
        <div className="outcome-art">
          <img src={`data:image/png;base64,${outcomeB64}`} alt="Illustration of this story beat" />
          <span className="outcome-caption">Ending illustration</span>
        </div>
      ) : null}
      {outcomePhase === "failed" ? (
        <p className="outcome-fallback">Illustration unavailable this round (offline API or generation skipped).</p>
      ) : null}
      {streamErr ? <p className="err">{streamErr}</p> : null}
    </>
  );

  const dialogueSection =
    showDialogue && !showNeuroDock ? <section className="dialogue">{dialogueBody}</section> : null;

  const dialogueSectionUnderDock =
    showDialogue && showNeuroDock ? (
      <section className="dialogue dialogue--under-dock" aria-label="Narrator response">
        {dialogueBody}
      </section>
    ) : null;

  const finalAnswerBlock = awaitingFree ? (
    <div className="neurobot">
      <label htmlFor="neurobot-in">Your final answer</label>
      <textarea
        id="neurobot-in"
        rows={4}
        className="neurobot-text"
        value={freeDraft}
        onChange={(e) => setFreeDraft(e.target.value)}
        disabled={streaming || ended}
        placeholder="What do you say or do?"
      />
      <button
        type="button"
        className="send-btn"
        disabled={streaming || ended || !freeDraft.trim()}
        onClick={() => void onSubmitFreeText()}
      >
        Send to NeuroBot
      </button>
    </div>
  ) : null;

  const neuroDockAside = (
    <aside className="neuro-investigate neuro-investigate--dock" aria-label="NeuroBot investigate chat">
      <h3 className="neuro-investigate-title">Ask NeuroBot</h3>
      <p className="neuro-investigate-sub">
        Quick questions about the dilemma — fishing for the &quot;correct&quot; answer may cost neural score.
      </p>
      <div className="neuro-thread">
        {neuroMessages.map((m, i) =>
          m.role === "user" ? (
            <div key={`${i}-u`} className="neuro-row neuro-row-user">
              <span className="neuro-meta">You</span>
              <div className="neuro-bubble neuro-bubble-user">{m.text}</div>
            </div>
          ) : (
            <div key={`${i}-a`} className="neuro-row neuro-row-bot">
              <span className="neuro-meta">NeuroBot</span>
              <div className="neuro-bubble neuro-bubble-bot">{m.text}</div>
            </div>
          ),
        )}
      </div>
      <div className="neuro-ask-row">
        <input
          type="text"
          className="neuro-ask-input"
          value={neuroAsk}
          onChange={(e) => setNeuroAsk(e.target.value)}
          disabled={streaming || neuroSending}
          placeholder={neuroDockPlaceholder}
          onKeyDown={(e) => {
            if (e.key === "Enter") void sendNeuroInvestigate();
          }}
        />
        <button
          type="button"
          className="neuro-ask-btn"
          disabled={streaming || neuroSending || !neuroAsk.trim()}
          onClick={() => void sendNeuroInvestigate()}
        >
          Ask
        </button>
      </div>
    </aside>
  );

  return (
    <div
      className={`play-shell ${showScenarioHero ? "play-shell--wide" : ""}${awaitingMode ? " play-shell--mode-pick" : ""}${showNeuroDock ? " play-shell--neuro-dock" : ""}`}
    >
      <nav className="play-nav">
        <Link to="/">← Home</Link>
        <span className="pill">
          {snap.scenario.icon} {snap.scenario.title}
        </span>
        <span className="pill score">
          Neural score: <strong>{score}</strong>
        </span>
      </nav>

      {snap.outline_generation_error ? (
        <p className="play-outline-fallback" role="status">
          Using built-in scenario deck (AI outline unavailable): {snap.outline_generation_error}
        </p>
      ) : snap.scenario_mode === "dynamic" ? (
        <p className="play-outline-ok" role="status">
          AI-generated scenario from theme &quot;{slug}&quot;
        </p>
      ) : null}

      {showNeuroDock ? (
        <div className="play-neuro-layout">
          <div className="play-neuro-main">
            {heroBanner}
            {showNeuroDock &&
            awaitingFree &&
            !narrative &&
            !streaming &&
            !ended ? (
              <p className="free-text-neuro-hint">
                Chat with NeuroBot in the green panel on the right if you want, then send your final answer below.
              </p>
            ) : null}
            {aiOptionsStage}
            {dialogueSection}
            {finalAnswerBlock}
          </div>
          <div className="play-neuro-rail">
            {neuroDockAside}
            {dialogueSectionUnderDock}
          </div>
        </div>
      ) : (
        <>
          {heroBanner}
          {awaitingMode ? (
            <section className="mode-pick">
              <h2 className="mode-title">How should we handle this scenario?</h2>
              <p className="mode-sub">
                Choose once for this run — type into NeuroBot, or take AI-written multiple-choice options (with a
                score cost).
              </p>
              <div className="mode-cards">
                <button type="button" className="mode-card mode-card-a" disabled={streaming} onClick={() => pickAnswerMode("free_text")}>
                  <strong>1 · NeuroBot — type your answer</strong>
                  <span>You write what you say or do. NeuroBot grades it and narrates what happens next.</span>
                </button>
                <button type="button" className="mode-card mode-card-b" disabled={streaming} onClick={() => pickAnswerMode("ai_options")}>
                  <strong>2 · AI-suggested options</strong>
                  <span>Multiple AI-suggested paths (styled cards). Costs neural score — you asked the machine to spoon-feed moves.</span>
                </button>
              </div>
              {modeErr ? <p className="err">{modeErr}</p> : null}
            </section>
          ) : null}
          {aiOptionsStage}
          {dialogueSection}
          {finalAnswerBlock}
        </>
      )}

      <style>{`
        .play-shell {
          max-width: 720px;
          margin: 0 auto;
          padding: 1rem 0 2.5rem;
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }
        .play-shell--wide {
          max-width: 960px;
        }
        .play-shell--mode-pick.play-shell--wide {
          max-width: min(1296px, calc(100vw - 0.5rem));
        }
        .play-shell--neuro-dock {
          max-width: min(1180px, calc(100vw - 0.5rem));
        }
        .play-shell--neuro-dock.play-shell--mode-pick.play-shell--wide {
          max-width: min(1340px, calc(100vw - 0.5rem));
        }
        .play-neuro-layout {
          display: flex;
          flex-direction: row;
          align-items: flex-start;
          gap: 0.5rem;
          width: 100%;
        }
        .play-neuro-rail {
          display: flex;
          flex-direction: column;
          align-items: stretch;
          gap: 0.75rem;
          flex-shrink: 0;
          width: min(42vmin, 340px);
          max-width: 100%;
          margin-left: 2.35rem;
        }
        .play-neuro-main {
          flex: 1;
          min-width: 0;
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }
        .play-nav {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 0.65rem;
          font-weight: 800;
          font-size: 0.75rem;
          letter-spacing: 0.06em;
        }
        .play-nav a {
          color: ${theme.secondary};
          text-decoration: none;
        }
        .play-outline-fallback,
        .play-outline-ok {
          margin: 0 0 0.5rem;
          padding: 0.45rem 0.65rem;
          border-radius: 10px;
          font-size: 0.78rem;
          line-height: 1.35;
          max-width: 52rem;
        }
        .play-outline-fallback {
          background: color-mix(in srgb, #fef3c7 85%, transparent);
          border: 1px solid color-mix(in srgb, #d97706 35%, transparent);
          color: ${theme.onSurface};
        }
        .play-outline-ok {
          background: color-mix(in srgb, ${theme.surfaceHigh} 70%, #e0f2fe);
          border: 1px solid color-mix(in srgb, ${theme.outline} 40%, transparent);
          color: color-mix(in srgb, ${theme.onSurface} 88%, gray);
        }
        .pill {
          padding: 0.35rem 0.75rem;
          border-radius: 999px;
          background: color-mix(in srgb, ${theme.surfaceHigh} 80%, white);
          border: 1px solid color-mix(in srgb, ${theme.outline} 45%, transparent);
        }
        .pill.score strong { color: ${theme.primary}; }
        .mode-pick {
          padding: 1rem 1.1rem;
          border-radius: 16px;
          background: color-mix(in srgb, ${theme.surfaceLow} 90%, white);
          border: 2px solid color-mix(in srgb, ${theme.outline} 50%, transparent);
        }
        .mode-title {
          margin: 0 0 0.35rem;
          font-size: 1.05rem;
          font-weight: 900;
          color: ${theme.onSurface};
        }
        .mode-sub {
          margin: 0 0 1rem;
          font-size: 0.85rem;
          line-height: 1.45;
          color: color-mix(in srgb, ${theme.onSurface} 85%, gray);
        }
        .mode-cards {
          display: flex;
          flex-direction: column;
          gap: 0.65rem;
        }
        .mode-card {
          text-align: left;
          padding: 0.85rem 1rem;
          border-radius: 14px;
          border: 2px solid color-mix(in srgb, ${theme.outline} 55%, transparent);
          background: ${theme.surface};
          font-family: inherit;
          cursor: pointer;
          transition: transform 0.06s ease, filter 0.1s ease;
        }
        .mode-card:hover:not(:disabled) {
          filter: brightness(1.02);
          transform: translateY(-1px);
        }
        .mode-card:disabled { opacity: 0.55; cursor: not-allowed; }
        .mode-card strong {
          display: block;
          font-size: 0.88rem;
          margin-bottom: 0.35rem;
          color: ${theme.onSurface};
        }
        .mode-card span {
          font-size: 0.8rem;
          line-height: 1.45;
          color: color-mix(in srgb, ${theme.onSurface} 88%, gray);
        }
        .mode-card-a { border-left: 4px solid ${theme.secondary}; }
        .mode-card-b { border-left: 4px solid ${theme.primary}; }
        .dialogue {
          padding: 1rem 1.1rem;
          border-radius: 16px;
          background: color-mix(in srgb, ${theme.surface} 92%, transparent);
          border: 1px solid color-mix(in srgb, ${theme.outline} 40%, transparent);
          box-shadow: 0 18px 40px color-mix(in srgb, ${theme.onSurface} 12%, transparent);
          min-height: 120px;
        }
        .dialogue--under-dock {
          min-height: 8rem;
          margin: 0;
          width: 100%;
          box-sizing: border-box;
          padding: 1.125rem 0.95rem;
          font-size: 1.0625rem;
          border: 3px solid #a865b5;
          box-shadow: 0 14px 32px rgba(168, 101, 181, 0.28), 0 0 0 1px rgba(168, 101, 181, 0.35) inset;
        }
        .dialogue--under-dock .stream-box {
          min-height: 3rem;
          font-size: 1rem;
          line-height: 1.55;
        }
        .dialogue--under-dock .static-line {
          font-size: 1em;
        }
        .dialogue--under-dock .fin {
          font-size: 1em;
        }
        .dialogue--under-dock .achievement {
          font-size: 0.92em;
        }
        .static-line { margin: 0 0 0.65rem; line-height: 1.45; color: ${theme.onSurface}; }
        .free-text-neuro-hint {
          margin: 0;
          font-size: 0.88rem;
          line-height: 1.45;
          font-style: italic;
          opacity: 0.72;
          color: color-mix(in srgb, ${theme.onSurface} 88%, gray);
        }
        .stream-box {
          font-size: 0.95rem;
          line-height: 1.5;
          min-height: 3rem;
          white-space: pre-wrap;
        }
        .cursor { animation: blink 1s step-end infinite; color: ${theme.secondary}; }
        @keyframes blink { 50% { opacity: 0; } }
        .fin { margin: 0.5rem 0 0; font-weight: 700; color: ${theme.secondary}; }
        .achievement {
          margin-bottom: 0.65rem;
          padding: 0.5rem 0.65rem;
          border-radius: 10px;
          background: linear-gradient(145deg, #ffd76a, #f2a900);
          font-weight: 800;
          font-size: 0.82rem;
        }
        .err { color: ${theme.primary}; font-weight: 700; margin: 0.35rem 0 0; }
        .neuro-investigate-title {
          margin: 0 0 0.25rem;
          font-size: 0.88rem;
          font-weight: 900;
          color: ${theme.onSurface};
        }
        .neuro-investigate-sub {
          margin: 0 0 0.65rem;
          font-size: 0.76rem;
          line-height: 1.4;
          color: color-mix(in srgb, ${theme.onSurface} 82%, gray);
        }
        .neuro-investigate--dock {
          flex-shrink: 0;
          margin-left: 0;
          box-sizing: border-box;
          width: 100%;
          aspect-ratio: 1 / 1;
          max-width: 100%;
          padding: 0.52rem 0.58rem;
          border-radius: 14px;
          background: linear-gradient(165deg, #acd8a7 0%, #9dc896 42%, #87ae73 100%);
          border: 3px solid #5d7d54;
          box-shadow: 4px 6px 0 rgba(93, 125, 84, 0.28);
          display: flex;
          flex-direction: column;
          position: sticky;
          top: 0.75rem;
        }
        .neuro-investigate--dock .neuro-investigate-title {
          color: #2f4a2c;
          font-size: 0.93rem;
        }
        .neuro-investigate--dock .neuro-investigate-sub {
          color: #3d5238;
          margin-bottom: 0.4rem;
          font-size: 0.76rem;
          line-height: 1.38;
        }
        .neuro-thread {
          display: flex;
          flex-direction: column;
          gap: 0.45rem;
          max-height: 14rem;
          overflow-y: auto;
          margin-bottom: 0.55rem;
        }
        .neuro-investigate--dock .neuro-thread {
          flex: 1;
          min-height: 0;
          max-height: none;
          margin-bottom: 0.4rem;
        }
        .neuro-row { display: flex; flex-direction: column; gap: 0.15rem; }
        .neuro-row-user { align-items: flex-end; }
        .neuro-row-bot { align-items: flex-start; }
        .neuro-meta {
          font-size: 0.62rem;
          font-weight: 800;
          letter-spacing: 0.06em;
          color: color-mix(in srgb, ${theme.onSurface} 65%, gray);
        }
        .neuro-row-user .neuro-meta { color: ${theme.secondary}; }
        .neuro-row-bot .neuro-meta { color: ${theme.primary}; }
        .neuro-investigate--dock .neuro-meta {
          color: #4a6b44;
          font-size: 0.72rem;
        }
        .neuro-investigate--dock .neuro-row-user .neuro-meta {
          color: #2f4a2c;
        }
        .neuro-investigate--dock .neuro-row-bot .neuro-meta {
          color: #3d5238;
        }
        .neuro-bubble {
          max-width: 95%;
          padding: 0.45rem 0.65rem;
          border-radius: 12px;
          font-size: 0.82rem;
          line-height: 1.45;
        }
        .neuro-bubble-user {
          background: ${theme.secondary};
          color: white;
          border-radius: 12px 4px 12px 12px;
        }
        .neuro-bubble-bot {
          background: white;
          color: ${theme.onSurface};
          border: 2px solid color-mix(in srgb, ${theme.outline} 35%, transparent);
          border-radius: 4px 12px 12px 12px;
        }
        .neuro-investigate--dock .neuro-bubble-user {
          background: #5d7d54;
          color: #f5faf4;
          border: 2px solid #4a6844;
          font-size: 0.93rem;
          line-height: 1.42;
        }
        .neuro-investigate--dock .neuro-bubble-bot {
          background: #eef6ec;
          color: #2f4a2c;
          border: 2px solid #87ae73;
          font-size: 0.93rem;
          line-height: 1.42;
        }
        .neuro-ask-row {
          display: flex;
          gap: 0.45rem;
          align-items: center;
        }
        .neuro-ask-input {
          flex: 1;
          min-width: 0;
          font-family: inherit;
          font-size: 0.85rem;
          padding: 0.5rem 0.65rem;
          border-radius: 10px;
          border: 2px solid color-mix(in srgb, ${theme.outline} 50%, transparent);
        }
        .neuro-investigate--dock .neuro-ask-input {
          border-color: #6d9665;
          background: #f5faf4;
          font-size: 0.88rem;
          padding: 0.55rem 0.7rem;
        }
        .neuro-ask-btn {
          flex-shrink: 0;
          padding: 0.5rem 0.85rem;
          border-radius: 10px;
          border: 2px solid ${theme.onSurface};
          background: ${theme.surfaceHigh};
          font-weight: 800;
          font-size: 0.78rem;
          cursor: pointer;
          font-family: inherit;
        }
        .neuro-investigate--dock .neuro-ask-btn {
          background: #87ae73;
          border-color: #4d6848;
          color: #1e2e1c;
          font-size: 0.85rem;
          padding: 0.55rem 0.9rem;
        }
        .neuro-ask-btn:disabled {
          opacity: 0.45;
          cursor: not-allowed;
        }
        .neurobot {
          display: flex;
          flex-direction: column;
          gap: 0.45rem;
        }
        .neurobot label {
          font-weight: 800;
          font-size: 0.78rem;
          letter-spacing: 0.06em;
          color: ${theme.onSurface};
        }
        .neurobot-text {
          font-family: inherit;
          font-size: 0.9rem;
          padding: 0.65rem 0.75rem;
          border-radius: 12px;
          border: 2px solid color-mix(in srgb, ${theme.outline} 55%, transparent);
          resize: vertical;
          min-height: 5rem;
        }
        .neurobot-text:disabled {
          opacity: 0.55;
        }
        .send-btn {
          align-self: flex-start;
          padding: 0.55rem 1.1rem;
          border-radius: 12px;
          border: 2px solid ${theme.onSurface};
          background: ${theme.secondary};
          color: white;
          font-weight: 800;
          font-size: 0.82rem;
          cursor: pointer;
          font-family: inherit;
        }
        .send-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .ai-options-stage {
          display: flex;
          flex-direction: column;
          gap: 1.25rem;
        }
        .ai-options-hint {
          margin: 0;
          font-size: 0.88rem;
          line-height: 1.45;
          font-style: italic;
          opacity: 0.72;
          color: color-mix(in srgb, ${theme.onSurface} 88%, gray);
        }
        .ai-scenario-hero {
          display: flex;
          flex-wrap: wrap;
          align-items: stretch;
          gap: 1rem 1.25rem;
          padding: 1.25rem 1.35rem;
          background: linear-gradient(160deg, #fefce8 0%, #fef9c3 55%, #fde68a 100%);
          border: 2px solid #ffffff;
          border-radius: 14px;
          box-shadow: 6px 8px 0 rgba(61, 57, 4, 0.12);
          transform: rotate(-0.35deg);
        }
        .ai-scenario-hero-text {
          flex: 1 1 280px;
          min-width: 0;
        }
        .ai-scenario-pill {
          display: inline-block;
          padding: 0.22rem 0.55rem;
          border-radius: 999px;
          background: ${theme.primary};
          color: #ffffff;
          font-size: 0.62rem;
          font-weight: 900;
          letter-spacing: 0.08em;
        }
        .ai-scenario-num {
          margin: 0.65rem 0 0;
          font-size: 0.92rem;
          font-weight: 900;
          color: #5c5310;
          letter-spacing: 0.05em;
        }
        .ai-scenario-title {
          margin: 0.1rem 0 0.45rem;
          font-size: clamp(1.25rem, 2.8vw, 1.75rem);
          font-weight: 900;
          font-style: italic;
          color: ${theme.primary};
          letter-spacing: 0.03em;
          line-height: 1.08;
        }
        .ai-scenario-desc {
          margin: 0;
          font-size: 0.86rem;
          line-height: 1.48;
          color: #3d3904;
        }
        .ai-scenario-body-extra {
          display: block;
          margin-top: 0.4rem;
          font-size: 0.78rem;
          opacity: 0.88;
          line-height: 1.42;
        }
        .ai-scenario-footpill {
          display: inline-block;
          margin-top: 0.55rem;
          padding: 0.28rem 0.55rem;
          border-radius: 8px;
          background: rgba(255, 255, 255, 0.72);
          border: 1px solid rgba(61, 57, 4, 0.14);
          font-size: 0.7rem;
          font-weight: 800;
          color: #5c5310;
        }
        .ai-scenario-polaroid {
          flex: 0 1 200px;
          margin-left: auto;
          margin-right: auto;
          padding: 0.55rem 0.55rem 1.1rem;
          background: #ffffff;
          border-radius: 3px;
          box-shadow: 4px 7px 18px rgba(0, 0, 0, 0.14);
          transform: rotate(2deg);
          display: flex;
          flex-direction: column;
          align-items: stretch;
          gap: 0.4rem;
          min-width: 0;
        }
        .ai-scenario-polaroid-frame {
          position: relative;
          border-radius: 2px;
          overflow: hidden;
        }
        .ai-scenario-polaroid-overlay {
          position: absolute;
          inset: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          background: rgba(255, 255, 255, 0.62);
          backdrop-filter: blur(2px);
        }
        .ai-scenario-polaroid-spinner {
          width: 28px;
          height: 28px;
          border: 3px solid color-mix(in srgb, ${theme.primary} 22%, transparent);
          border-top-color: ${theme.primary};
          border-radius: 50%;
          animation: ai-scenario-polaroid-spin 0.7s linear infinite;
        }
        @keyframes ai-scenario-polaroid-spin {
          to {
            transform: rotate(360deg);
          }
        }
        .ai-scenario-polaroid-caption {
          display: block;
          margin: 0;
          padding: 0 0.1rem;
          font-size: 0.65rem;
          font-weight: 700;
          font-style: italic;
          line-height: 1.35;
          opacity: 0.78;
          color: #3d3904;
          text-align: center;
        }
        .ai-scenario-polaroid-caption--fallback {
          font-style: normal;
          font-weight: 600;
          opacity: 0.72;
          color: color-mix(in srgb, ${theme.onSurface} 72%, #5c5310);
        }
        .ai-scenario-polaroid-caption-wrap {
          display: flex;
          flex-direction: column;
          gap: 0.28rem;
          align-items: center;
        }
        .ai-scenario-polaroid-detail {
          display: block;
          margin: 0;
          padding: 0 0.15rem;
          font-size: 0.58rem;
          font-weight: 600;
          line-height: 1.38;
          opacity: 0.78;
          color: color-mix(in srgb, ${theme.onSurface} 78%, #5c5310);
          text-align: center;
          max-width: 280px;
        }
        .ai-scenario-polaroid-img {
          display: block;
          width: 100%;
          max-width: 220px;
          height: auto;
          aspect-ratio: 1;
          object-fit: cover;
          border-radius: 2px;
        }
        .ai-scenario-hero--enlarged {
          padding: 1.6875rem 1.8225rem;
          gap: 1.35rem 1.6875rem;
          border-radius: 18.9px;
          border-width: 2.5px;
          box-shadow: 8.1px 10.8px 0 rgba(61, 57, 4, 0.12);
        }
        .ai-scenario-hero--enlarged .ai-scenario-hero-text {
          flex: 1 1 378px;
        }
        .ai-scenario-hero--enlarged .ai-scenario-pill {
          padding: 0.297rem 0.7425rem;
          font-size: 0.837rem;
        }
        .ai-scenario-hero--enlarged .ai-scenario-num {
          margin: 0.8775rem 0 0;
          font-size: 1.242rem;
        }
        .ai-scenario-hero--enlarged .ai-scenario-title {
          margin: 0.135rem 0 0.6075rem;
          font-size: clamp(1.6875rem, 3.78vw, 2.3625rem);
        }
        .ai-scenario-hero--enlarged .ai-scenario-desc {
          font-size: 1.161rem;
          line-height: 1.48;
        }
        .ai-scenario-hero--enlarged .ai-scenario-body-extra {
          margin-top: 0.54rem;
          font-size: 1.053rem;
          line-height: 1.42;
        }
        .ai-scenario-hero--enlarged .ai-scenario-footpill {
          margin-top: 0.7425rem;
          padding: 0.378rem 0.7425rem;
          border-radius: 10.8px;
          font-size: 0.945rem;
        }
        .ai-scenario-hero--enlarged .ai-scenario-polaroid {
          flex: 0 1 270px;
          padding: 0.7425rem 0.7425rem 1.485rem;
          border-radius: 3.6px;
          box-shadow: 5.4px 9px 24.3px rgba(0, 0, 0, 0.14);
          gap: 0.54rem;
        }
        .ai-scenario-hero--enlarged .ai-scenario-polaroid-spinner {
          width: 37.8px;
          height: 37.8px;
          border-width: 4.05px;
        }
        .ai-scenario-hero--enlarged .ai-scenario-polaroid-caption {
          font-size: 0.8775rem;
        }
        .ai-scenario-hero--enlarged .ai-scenario-polaroid-detail {
          font-size: 0.783rem;
          max-width: 378px;
        }
        .ai-scenario-hero--enlarged .ai-scenario-polaroid-img {
          max-width: 297px;
          border-radius: 2.7px;
        }
        .ai-choice-grid {
          display: grid;
          grid-template-columns: 1fr;
          gap: 0.75rem;
        }
        @media (min-width: 640px) {
          .ai-choice-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
        }
        .ai-path-card {
          display: flex;
          flex-direction: column;
          align-items: flex-start;
          gap: 0.4rem;
          min-height: 10.5rem;
          padding: 1rem 1.05rem;
          border-radius: 14px;
          border: none;
          text-align: left;
          cursor: pointer;
          font-family: inherit;
          transition: transform 0.08s ease, box-shadow 0.08s ease;
          box-shadow: 0 4px 14px rgba(61, 57, 4, 0.1);
        }
        .ai-path-card:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 10px 26px rgba(61, 57, 4, 0.14);
        }
        .ai-path-card:disabled {
          opacity: 0.55;
          cursor: not-allowed;
        }
        .ai-path-card-top {
          display: flex;
          align-items: center;
          justify-content: space-between;
          width: 100%;
          gap: 0.5rem;
        }
        .ai-path-icon {
          display: grid;
          place-items: center;
          width: 2rem;
          height: 2rem;
          border-radius: 50%;
          font-weight: 900;
          font-size: 0.85rem;
          flex-shrink: 0;
        }
        .ai-path-badge {
          font-size: 0.56rem;
          font-weight: 900;
          letter-spacing: 0.07em;
          padding: 0.22rem 0.48rem;
          border-radius: 6px;
          text-align: center;
          line-height: 1.2;
        }
        .ai-path-title {
          font-weight: 900;
          font-size: 0.92rem;
          line-height: 1.28;
        }
        .ai-path-desc {
          font-size: 0.76rem;
          line-height: 1.42;
          flex: 1;
          opacity: 0.94;
        }
        .ai-path-cta {
          margin-top: auto;
          padding-top: 0.25rem;
          font-size: 0.68rem;
          font-weight: 900;
          letter-spacing: 0.07em;
        }

        .ai-path-card--hard {
          background: #ffffff;
          border: 2px solid rgba(61, 57, 4, 0.1);
          color: #3d3904;
        }
        .ai-path-card--hard .ai-path-icon {
          background: ${theme.primary};
          color: #ffffff;
        }
        .ai-path-card--hard .ai-path-badge {
          background: ${theme.primary};
          color: #ffffff;
        }
        .ai-path-card--hard .ai-path-cta {
          color: ${theme.primary};
        }

        .ai-path-card--easy {
          background: #155e75;
          color: #ecfeff;
          border: 2px solid #0c4a6e;
        }
        .ai-path-card--easy .ai-path-icon {
          background: rgba(255, 255, 255, 0.22);
        }
        .ai-path-card--easy .ai-path-badge {
          background: #67e8f9;
          color: #0c4a6e;
        }

        .ai-path-card--lazy {
          background: #3f6212;
          color: #f7fee7;
          border: 2px solid #365314;
        }
        .ai-path-card--lazy .ai-path-icon {
          background: rgba(255, 255, 255, 0.18);
        }
        .ai-path-card--lazy .ai-path-badge {
          background: #bef264;
          color: #1a2e05;
        }

        .ai-path-card--chaos {
          background: #fef9c3;
          color: #422006;
          border: 2px solid #ca8a04;
        }
        .ai-path-card--chaos .ai-path-icon {
          background: #422006;
          color: #fef9c3;
        }
        .ai-path-card--chaos .ai-path-badge {
          background: #ffffff;
          color: #422006;
          border: 1px solid #ca8a04;
        }
        .ai-path-card--chaos .ai-path-cta {
          color: #713f12;
        }
        @media (max-width: 820px) {
          .play-neuro-layout {
            flex-direction: column;
          }
          .play-neuro-rail {
            width: min(100%, 360px);
            margin-left: 0;
            align-self: flex-end;
          }
          .neuro-investigate--dock {
            width: min(100%, 360px);
            margin-left: 0;
            align-self: flex-end;
            position: relative;
            top: auto;
          }
        }
      `}</style>
    </div>
  );
}
