import { useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { fetchScenarios, type ScenarioSummary } from "./api";
import { GameChrome } from "./GameChrome";

const SCENARIO_ORDER = ["ai_overuse", "hallucination", "ethics"] as const;

function sortScenarios(list: ScenarioSummary[]): ScenarioSummary[] {
  const bySlug = Object.fromEntries(list.map((s) => [s.slug, s]));
  const ordered = SCENARIO_ORDER.map((slug) => bySlug[slug]).filter(Boolean) as ScenarioSummary[];
  const rest = list.filter((s) => !SCENARIO_ORDER.includes(s.slug as (typeof SCENARIO_ORDER)[number]));
  return [...ordered, ...rest];
}

/** Card blurbs from topic-selection mock (distinct from API body copy). */
const CARD_TEASER: Record<string, string> = {
  ai_overuse: "Let the algorithm choose your spouse. What could go wrong?",
  hallucination: "Confidently explaining why the moon is made of blue cheese since 2023.",
  ethics: "Trying to teach a calculator the difference between right, wrong, and 'profitable'.",
};

const SIDEBAR_ICONS: Record<string, string> = {
  ai_overuse: "🧠",
  hallucination: "👁️",
  ethics: "⚖️",
};

const TASK_BTN_CLASS = ["topic-task-blue", "topic-task-green", "topic-task-red"] as const;

export function TopicSelect() {
  const { state } = useLocation() as { state?: { slug?: string } | null };
  const [list, setList] = useState<ScenarioSummary[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [selectedSlug, setSelectedSlug] = useState<string>(state?.slug ?? "ai_overuse");

  useEffect(() => {
    fetchScenarios()
      .then((rows) => {
        setList(sortScenarios(rows));
        const focus = state?.slug;
        if (focus && rows.some((r) => r.slug === focus)) {
          setSelectedSlug(focus);
        } else {
          const first = sortScenarios(rows)[0];
          if (first) setSelectedSlug(first.slug);
        }
      })
      .catch(() => setErr("Could not load scenarios. Is the API running?"));
  }, [state?.slug]);

  const scenarios = useMemo(() => sortScenarios(list), [list]);

  const displayScenarios = scenarios.map((s) => ({
    ...s,
    icon: SIDEBAR_ICONS[s.slug] ?? s.icon,
    teaser: CARD_TEASER[s.slug] ?? s.tagline,
  }));

  return (
    <GameChrome scenarios={displayScenarios} selectedSlug={selectedSlug} error={err}>
      <main className="topic-main">
        <h1 className="topic-page-title">
          AI is taking over, hallucinating, and making questionable choices.{" "}
          <span className="topic-page-title-line">Which disaster would you like to manage today?</span>
        </h1>

        <div className="topic-grid">
          {displayScenarios.map((s, index) => (
            <article key={s.slug} className="topic-card">
              <TopicCardArt slug={s.slug} title={s.title} />
              <div className="topic-card-body">
                <h2 className="topic-card-title">{s.title}</h2>
                <p className="topic-card-desc">{s.teaser}</p>
                <Link to={`/play/${s.slug}`} className={`topic-task-btn ${TASK_BTN_CLASS[index % 3]}`}>
                  SELECT TASK
                </Link>
              </div>
            </article>
          ))}
        </div>

        <style>{TOPIC_CSS}</style>
      </main>
    </GameChrome>
  );
}

function TopicCardArt({ slug, title }: { slug: string; title: string }) {
  const src = CARD_ART[slug];
  if (src) {
    return (
      <div className="topic-card-visual">
        <img src={src} alt={title} className="topic-card-img" decoding="async" />
      </div>
    );
  }
  return (
    <div className={`topic-card-visual topic-card-fallback topic-fallback-${slug}`} role="img" aria-label={title}>
      <span className="topic-fallback-emoji">{FALLBACK_EMOJI[slug] ?? "🎮"}</span>
    </div>
  );
}

const CARD_ART: Record<string, string> = {
  ai_overuse: "/topics/ai-overuse.png",
  hallucination: "/topics/hallucination.png",
  ethics: "/topics/ethics.png",
};

const FALLBACK_EMOJI: Record<string, string> = {
  ai_overuse: "🤖",
  hallucination: "🖥️",
  ethics: "⚖️",
};

const TOPIC_CSS = `
        .topic-main {
          flex: 1;
          background: #fffef6;
          padding: 1.5rem 1rem 2.5rem;
          min-width: 0;
        }
        @media (min-width: 900px) {
          .topic-main {
            padding: 2rem 1.75rem 2.5rem;
          }
        }

        .topic-page-title {
          margin: 0 auto 1.75rem;
          max-width: 52rem;
          text-align: center;
          font-weight: 900;
          font-size: clamp(1rem, 2.4vw, 1.35rem);
          line-height: 1.35;
          color: #3d3904;
        }
        .topic-page-title-line {
          display: block;
          margin-top: 0.35rem;
        }

        .topic-grid {
          display: grid;
          grid-template-columns: 1fr;
          gap: 1.5rem;
          width: 100%;
          max-width: 100%;
          margin: 0 auto;
        }
        @media (min-width: 700px) {
          .topic-grid {
            grid-template-columns: repeat(3, 1fr);
            gap: 1.5rem;
            align-items: stretch;
          }
        }

        .topic-card {
          background: #ffffff;
          border-radius: 14px;
          overflow: hidden;
          box-shadow: 0 10px 28px rgba(61, 57, 4, 0.12);
          border: 2px solid rgba(61, 57, 4, 0.08);
          display: flex;
          flex-direction: column;
        }

        .topic-card-visual {
          width: 100%;
          aspect-ratio: 1 / 1;
          display: flex;
          align-items: center;
          justify-content: center;
          overflow: hidden;
          background: linear-gradient(180deg, #e3f2fd 0%, #fafafa 100%);
          border-bottom: 2px solid rgba(61, 57, 4, 0.06);
        }
        .topic-card-img {
          width: 100%;
          height: 100%;
          object-fit: contain;
          object-position: center;
        }

        .topic-card-fallback {
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .topic-fallback-ai_overuse {
          background: linear-gradient(180deg, #ffe0b2 0%, #fff8e1 100%);
        }
        .topic-fallback-hallucination {
          background: linear-gradient(180deg, #e1bee7 0%, #f3e5f5 100%);
        }
        .topic-fallback-ethics {
          background: linear-gradient(180deg, #c8e6c9 0%, #e8f5e9 100%);
        }
        .topic-fallback-emoji {
          font-size: clamp(3.5rem, 12vw, 5rem);
          line-height: 1;
          filter: drop-shadow(2px 2px 0 rgba(61, 57, 4, 0.15));
        }

        .topic-card-body {
          padding: 1rem 1.1rem 1.25rem;
          display: flex;
          flex-direction: column;
          flex: 1;
          gap: 0.5rem;
        }
        .topic-card-title {
          margin: 0;
          font-size: 1.05rem;
          font-weight: 900;
          color: #3d3904;
        }
        .topic-card-desc {
          margin: 0;
          flex: 1;
          font-size: 0.88rem;
          line-height: 1.45;
          color: #4a4420;
        }

        .topic-task-btn {
          margin-top: 0.5rem;
          display: block;
          text-align: center;
          padding: 0.65rem 1rem;
          font-family: inherit;
          font-weight: 900;
          font-size: 0.78rem;
          letter-spacing: 0.08em;
          color: #ffffff;
          text-decoration: none;
          border-radius: 10px;
          border: 2px solid #3d3904;
          box-shadow: 4px 4px 0 #3d3904;
          transition: transform 0.08s ease, box-shadow 0.08s ease;
        }
        .topic-task-btn:hover {
          transform: translate(2px, 2px);
          box-shadow: 2px 2px 0 #3d3904;
          color: #ffffff;
        }
        .topic-task-blue {
          background: #2563eb;
        }
        .topic-task-green {
          background: #16a34a;
        }
        .topic-task-red {
          background: #cb0319;
        }
`;
