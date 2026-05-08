import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  consumeSessionStream,
  createSession,
  submitChoice,
  type SessionSnapshot,
  type StatePatch,
} from "./api";
import { PhaserGame } from "./PhaserGame";
import { theme } from "./theme";

const ARCHIVE_KEY = "sure_archives_v1";

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
  const [snap, setSnap] = useState<SessionSnapshot | null>(null);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const [streamErr, setStreamErr] = useState<string | null>(null);
  const [narrative, setNarrative] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [choices, setChoices] = useState<string[]>([]);
  const [staticLine, setStaticLine] = useState<string | null>(null);
  const [ended, setEnded] = useState(false);
  const [achievement, setAchievement] = useState<string | null>(null);
  const [score, setScore] = useState(50);

  useEffect(() => {
    if (!slug) return;
    createSession(slug)
      .then((s) => {
        setSnap(s);
        setChoices(s.choices);
        setStaticLine(s.static_line ?? null);
        setScore(s.neural_score);
      })
      .catch(() => setLoadErr("Could not start session."));
  }, [slug]);

  const runStream = useCallback(async () => {
    if (!snap) return;
    setStreaming(true);
    setStreamErr(null);
    setNarrative("");
    try {
      await consumeSessionStream(snap.session_id, {
        onToken: (t) => setNarrative((prev) => prev + t),
        onStatePatch: (p: StatePatch) => {
          setScore(p.neural_score);
          if (p.choices) setChoices(p.choices);
          if ("static_line" in p) setStaticLine(p.static_line ?? null);
          if (p.achievement_unlocked) setAchievement(p.achievement_unlocked);
          if (p.ended) {
            setEnded(true);
            pushArchive({
              slug: snap.scenario.slug,
              title: snap.scenario.title,
              score: p.neural_score,
              achievement: p.achievement_unlocked ?? null,
            });
          }
        },
        onDone: () => setStreaming(false),
        onError: (msg) => {
          setStreamErr(msg);
          setStreaming(false);
        },
      });
    } catch {
      setStreamErr("stream_failed");
      setStreaming(false);
    }
  }, [snap]);

  const onPick = async (idx: number) => {
    if (!snap || streaming || ended) return;
    try {
      await submitChoice(snap.session_id, idx);
      await runStream();
    } catch {
      setStreamErr("choice_failed");
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
        <p>Loading…</p>
      </div>
    );
  }

  return (
    <div className="play-shell">
      <nav className="play-nav">
        <Link to="/">← Home</Link>
        <span className="pill">
          {snap.scenario.icon} {snap.scenario.title}
        </span>
        <span className="pill score">
          Neural score: <strong>{score}</strong>
        </span>
      </nav>

      <PhaserGame height={300} />

      <section className="dialogue">
        {achievement && (
          <div className="achievement">
            Achievement unlocked: <strong>{achievement}</strong>
          </div>
        )}
        {staticLine && (
          <p className="static-line">
            <em>{staticLine}</em>
          </p>
        )}
        <div className="stream-box">
          {narrative || (streaming ? <span className="cursor">▍</span> : null)}
          {!narrative && !streaming && !ended && (
            <span className="hint">Pick a move — the narrator reacts in real time.</span>
          )}
          {ended && <p className="fin">Run complete. Your conscience may require a reboot.</p>}
        </div>
        {streamErr && <p className="err">{streamErr}</p>}
      </section>

      <div className="choices">
        {choices.map((c, i) => (
          <button
            key={`${i}-${c}`}
            type="button"
            className="choice-btn"
            disabled={streaming || ended}
            onClick={() => onPick(i)}
          >
            {c}
          </button>
        ))}
      </div>

      <style>{`
        .play-shell {
          max-width: 720px;
          margin: 0 auto;
          padding: 1rem 1.25rem 2.5rem;
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
        .pill {
          padding: 0.35rem 0.75rem;
          border-radius: 999px;
          background: color-mix(in srgb, ${theme.surfaceHigh} 80%, white);
          border: 1px solid color-mix(in srgb, ${theme.outline} 45%, transparent);
        }
        .pill.score strong { color: ${theme.primary}; }
        .dialogue {
          padding: 1rem 1.1rem;
          border-radius: 16px;
          background: color-mix(in srgb, ${theme.surface} 92%, transparent);
          border: 1px solid color-mix(in srgb, ${theme.outline} 40%, transparent);
          box-shadow: 0 18px 40px color-mix(in srgb, ${theme.onSurface} 12%, transparent);
          min-height: 120px;
        }
        .static-line { margin: 0 0 0.65rem; line-height: 1.45; color: ${theme.onSurface}; }
        .stream-box {
          font-size: 0.95rem;
          line-height: 1.5;
          min-height: 3rem;
          white-space: pre-wrap;
        }
        .hint { opacity: 0.65; font-style: italic; }
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
        .choices {
          display: flex;
          flex-direction: column;
          gap: 0.55rem;
        }
        .choice-btn {
          text-align: left;
          padding: 0.75rem 1rem;
          border-radius: 12px;
          border: 2px solid color-mix(in srgb, ${theme.outline} 55%, transparent);
          background: ${theme.surface};
          font-weight: 700;
          font-size: 0.88rem;
          color: ${theme.onSurface};
          transition: transform 0.06s ease, filter 0.1s ease;
        }
        .choice-btn:hover:not(:disabled) {
          filter: brightness(1.02);
          transform: translateY(-1px);
        }
        .choice-btn:disabled { opacity: 0.55; cursor: not-allowed; }
      `}</style>
    </div>
  );
}
