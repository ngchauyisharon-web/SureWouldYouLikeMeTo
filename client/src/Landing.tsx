import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { fetchScenarios, type ScenarioSummary } from "./api";
import { GameChrome } from "./GameChrome";

/** Canonical scenario order from the reference UI */
const SCENARIO_ORDER = ["ai_overuse", "hallucination", "ethics"] as const;

function sortScenarios(list: ScenarioSummary[]): ScenarioSummary[] {
  const bySlug = Object.fromEntries(list.map((s) => [s.slug, s]));
  const ordered = SCENARIO_ORDER.map((slug) => bySlug[slug]).filter(Boolean) as ScenarioSummary[];
  const rest = list.filter((s) => !SCENARIO_ORDER.includes(s.slug as (typeof SCENARIO_ORDER)[number]));
  return [...ordered, ...rest];
}

const SIDEBAR_ICONS: Record<string, string> = {
  ai_overuse: "🧠",
  hallucination: "👁️",
  ethics: "⚖️",
};

export function Landing() {
  const navigate = useNavigate();
  const [list, setList] = useState<ScenarioSummary[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [selectedSlug, setSelectedSlug] = useState<string>("ai_overuse");

  useEffect(() => {
    fetchScenarios()
      .then((rows) => {
        setList(sortScenarios(rows));
        if (rows.some((s) => s.slug === selectedSlug)) return;
        const first = sortScenarios(rows)[0];
        if (first) setSelectedSlug(first.slug);
      })
      .catch(() => setErr("Could not load scenarios. Is the API running?"));
  }, []);

  const scenarios = useMemo(() => sortScenarios(list), [list]);

  const displayScenarios = useMemo(
    () =>
      scenarios.map((s) => ({
        ...s,
        icon: SIDEBAR_ICONS[s.slug] ?? s.icon,
      })),
    [scenarios],
  );

  const startRun = () => {
    navigate("/topics", { state: { slug: selectedSlug } });
  };

  return (
    <GameChrome scenarios={displayScenarios} selectedSlug={selectedSlug}>
      <main className="ref-main">
        <div className="ref-main-inner">
          <h1 className="ref-sr-only">SURE! WOULD YOU LIKE ME TO...?</h1>

          {err ? <p className="ref-banner-err">{err}</p> : null}

          <div className="ref-hero-crop">
            <img
              src="/landing-hero.png"
              alt="Wide banner: grey robot with green eyes offers a pink brain to a skeptical South Park-style boy; red and black headline Sure! Would you like me to?; circular inset with a devious grinning face top right; cream sky, blue arc, clouds, and green bushes."
              className="ref-hero-img"
              decoding="async"
            />
          </div>

          <div className="ref-cta-row">
            <button type="button" className="ref-btn-start" onClick={startRun}>
              START
            </button>
            <Link to="/archives" className="ref-btn-achieve">
              <span className="ref-medal" aria-hidden>
                ⭐
              </span>
              ACHIEVEMENTS
            </Link>
          </div>
        </div>

        <style>{LANDING_MAIN_CSS}</style>
      </main>
    </GameChrome>
  );
}

const LANDING_MAIN_CSS = `
        .ref-main {
          flex: 1;
          min-height: 0;
          display: flex;
          flex-direction: column;
          position: relative;
          overflow: hidden;
          background: #fdf9ed;
        }

        .ref-main-inner {
          position: relative;
          z-index: 2;
          flex: 1;
          min-height: 0;
          padding: 0 0 0.75rem;
          display: flex;
          flex-direction: column;
          align-items: center;
          width: 100%;
        }

        .ref-sr-only {
          position: absolute;
          width: 1px;
          height: 1px;
          padding: 0;
          margin: -1px;
          overflow: hidden;
          clip: rect(0, 0, 0, 0);
          white-space: nowrap;
          border: 0;
        }

        .ref-banner-err {
          flex-shrink: 0;
          width: calc(100% - 2rem);
          max-width: 28rem;
          margin: 0.5rem 1rem 0;
          padding: 0.6rem 0.75rem;
          border: 2px solid #cb0319;
          border-radius: 10px;
          background: #ffe8e4;
          font-size: 0.85rem;
          font-weight: 700;
          color: #8b0000;
          text-align: center;
        }

        .ref-hero-crop {
          flex: 1 1 0;
          min-height: 0;
          width: 100%;
          overflow: hidden;
          background: #fdf9ed;
          display: flex;
          align-items: center;
          justify-content: center;
          line-height: 0;
        }
        .ref-hero-img {
          display: block;
          width: 100%;
          height: 100%;
          max-height: 100%;
          object-fit: contain;
          object-position: center bottom;
        }

        .ref-cta-row {
          flex-shrink: 0;
          display: flex;
          flex-wrap: wrap;
          gap: 1.3rem;
          justify-content: center;
          align-items: center;
          width: 100%;
          max-width: 676px;
          padding: 0.5rem 1rem 0;
          margin-top: 0.35rem;
        }
        .ref-btn-start {
          flex: 1;
          min-width: 182px;
          padding: 1.1rem 1.95rem;
          font-family: inherit;
          font-weight: 900;
          font-size: 1.755rem;
          letter-spacing: 0.06em;
          color: #ffffff;
          background: #cb0319;
          border: 4px solid #3d3904;
          border-radius: 18px;
          cursor: pointer;
          box-shadow: 8px 8px 0 #3d3904;
          transition: transform 0.1s ease, box-shadow 0.1s ease;
        }
        .ref-btn-start:hover {
          transform: translate(2px, 2px);
          box-shadow: 6px 6px 0 #3d3904;
        }
        .ref-btn-start:active {
          transform: translate(4px, 4px);
          box-shadow: 3px 3px 0 #3d3904;
        }
        .ref-btn-achieve {
          flex: 1;
          min-width: 208px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 0.65rem;
          padding: 1.1rem 1.625rem;
          font-family: inherit;
          font-weight: 900;
          font-size: 1.3rem;
          letter-spacing: 0.05em;
          color: #ffffff;
          background: #006c95;
          border: 4px solid #3d3904;
          border-radius: 18px;
          text-decoration: none;
          box-shadow: 8px 8px 0 #3d3904;
          transition: transform 0.1s ease, box-shadow 0.1s ease;
        }
        .ref-btn-achieve:hover {
          transform: translate(2px, 2px);
          box-shadow: 6px 6px 0 #3d3904;
          color: #ffffff;
        }
        .ref-btn-achieve:active {
          transform: translate(4px, 4px);
          box-shadow: 3px 3px 0 #3d3904;
        }
        .ref-medal {
          display: grid;
          place-items: center;
          width: 2.6rem;
          height: 2.6rem;
          border-radius: 50%;
          background: linear-gradient(145deg, #ffd76a, #f2a900);
          border: 2px solid #3d3904;
          font-size: 1.3rem;
        }

        @media (max-width: 899px) {
          .ref-main-inner {
            flex: none;
            min-height: 0;
          }
          .ref-hero-crop {
            flex: none;
            min-height: 12rem;
          }
          .ref-hero-img {
            height: auto;
            max-height: 55vh;
            object-fit: contain;
          }
        }
`;
