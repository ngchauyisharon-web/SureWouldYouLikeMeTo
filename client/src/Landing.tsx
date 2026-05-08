import { useEffect, useMemo, useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { fetchScenarios, type ScenarioSummary } from "./api";

/** Canonical scenario order from the reference UI */
const SCENARIO_ORDER = ["ai_overuse", "hallucination", "ethics"] as const;

function sortScenarios(list: ScenarioSummary[]): ScenarioSummary[] {
  const bySlug = Object.fromEntries(list.map((s) => [s.slug, s]));
  const ordered = SCENARIO_ORDER.map((slug) => bySlug[slug]).filter(Boolean) as ScenarioSummary[];
  const rest = list.filter((s) => !SCENARIO_ORDER.includes(s.slug as (typeof SCENARIO_ORDER)[number]));
  return [...ordered, ...rest];
}

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

  const startRun = () => {
    navigate(`/play/${selectedSlug}`);
  };

  return (
    <div className="ref-landing">
      {/* Top bar — logo left, nav center, help + avatar right */}
      <header className="ref-topnav">
        <div className="ref-topnav-inner">
          <span className="ref-logo">SURE! WOULD YOU LIKE ME TO...?</span>
          <nav className="ref-topnav-center" aria-label="Main">
            <NavLink to="/" end className={({ isActive }) => `ref-top-link ${isActive ? "ref-top-link-active" : ""}`}>
              PLAY
            </NavLink>
            <Link to="/archives" className="ref-top-link">
              ARCHIVES
            </Link>
            <Link to="/settings" className="ref-top-link">
              SETTINGS
            </Link>
          </nav>
          <div className="ref-topnav-right">
            <Link to="/help" className="ref-help-link">
              Help
            </Link>
            <div className="ref-avatar-ring" title="You">
              <img src="/sidebar-avatar.jpg" alt="" className="ref-avatar-img" />
            </div>
          </div>
        </div>
      </header>

      <div className="ref-body">
        {/* Left sidebar — neural + scenario pills + premise */}
        <aside className="ref-sidebar" aria-label="Scenarios">
          <div className="ref-neural">
            <span className="ref-brain" aria-hidden>
              🧠
            </span>
            <div>
              <p className="ref-neural-title">Neural Scoring</p>
              <p className="ref-neural-sub">Current State: Smoothing</p>
            </div>
          </div>

          <ul className="ref-scenario-list">
            {scenarios.map((s) => (
              <li key={s.slug}>
                <button
                  type="button"
                  className={`ref-scenario-pill ${selectedSlug === s.slug ? "ref-scenario-pill-active" : ""}`}
                  onClick={() => setSelectedSlug(s.slug)}
                >
                  <span className="ref-scenario-ico" aria-hidden>
                    {s.icon}
                  </span>
                  {s.title}
                </button>
              </li>
            ))}
          </ul>

          <p className="ref-premise">
            AI is taking over, hallucinating, and making questionable choices.{" "}
            <strong>Which disaster would you like to manage today?</strong>
          </p>
        </aside>

        {/* Main stage — sky, hills, headline, art, CTAs */}
        <main className="ref-main">
          <div className="ref-cloud ref-cloud-1" aria-hidden />
          <div className="ref-cloud ref-cloud-2" aria-hidden />
          <div className="ref-cloud ref-cloud-3" aria-hidden />
          <div className="ref-hills" aria-hidden />

          <div className="ref-main-inner">
            <h1 className="ref-hero-title">
              <span className="ref-sure">SURE!</span>
              <span className="ref-title-rest">WOULD YOU LIKE ME TO...?</span>
            </h1>

            {err ? <p className="ref-banner-err">{err}</p> : null}

            <div className="ref-stage-wrap">
              <div className="ref-float-head" title="Mood: optimistic">
                <img src="/sidebar-avatar.jpg" alt="" className="ref-float-img" />
              </div>
              <div className="ref-art-frame">
                <img
                  src="/landing-reference.png"
                  alt="Goofy robot holding a pink brain next to a skeptical boy"
                  className="ref-art-img"
                />
              </div>
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
        </main>
      </div>

      <style>{`
        .ref-landing {
          min-height: 100%;
          background: #fffbff;
          color: #3d3904;
          font-family: "Plus Jakarta Sans", system-ui, sans-serif;
        }

        .ref-topnav {
          background: #fffbff;
          border-bottom: 2px solid #3d3904;
        }
        .ref-topnav-inner {
          max-width: 1200px;
          margin: 0 auto;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 1rem;
          padding: 0.65rem 1.25rem;
          flex-wrap: wrap;
        }
        .ref-logo {
          font-weight: 900;
          font-style: italic;
          font-size: clamp(0.7rem, 1.5vw, 0.95rem);
          letter-spacing: 0.04em;
          color: #cb0319;
        }
        .ref-topnav-center {
          display: flex;
          align-items: center;
          gap: 1.75rem;
        }
        .ref-top-link {
          font-weight: 800;
          font-size: 0.75rem;
          letter-spacing: 0.12em;
          text-decoration: none;
          color: #3d3904;
          padding-bottom: 0.2rem;
          border-bottom: 4px solid transparent;
        }
        .ref-top-link:hover {
          color: #006c95;
        }
        .ref-top-link-active {
          border-bottom-color: #cb0319;
        }
        .ref-topnav-right {
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }
        .ref-help-link {
          font-weight: 800;
          font-size: 0.8rem;
          color: #3d3904;
          text-decoration: none;
        }
        .ref-help-link:hover {
          color: #cb0319;
        }
        .ref-avatar-ring {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          border: 2px solid #3d3904;
          overflow: hidden;
          background: #fff9e5;
        }
        .ref-avatar-img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .ref-body {
          display: flex;
          flex-direction: column;
          max-width: 1200px;
          margin: 0 auto;
        }
        @media (min-width: 900px) {
          .ref-body {
            flex-direction: row;
            align-items: stretch;
            min-height: calc(100vh - 56px);
          }
        }

        .ref-sidebar {
          background: #fff6dc;
          border-right: 3px solid #3d3904;
          padding: 1.25rem 1rem 1.5rem;
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }
        @media (min-width: 900px) {
          .ref-sidebar {
            width: 260px;
            flex-shrink: 0;
          }
        }

        .ref-neural {
          display: flex;
          gap: 0.65rem;
          align-items: flex-start;
        }
        .ref-brain {
          font-size: 1.75rem;
          filter: hue-rotate(-15deg) saturate(1.3);
        }
        .ref-neural-title {
          margin: 0;
          font-weight: 900;
          font-size: 0.95rem;
          color: #3d3904;
        }
        .ref-neural-sub {
          margin: 0.15rem 0 0;
          font-size: 0.78rem;
          font-weight: 700;
          color: #006c95;
        }

        .ref-scenario-list {
          list-style: none;
          margin: 0;
          padding: 0;
          display: flex;
          flex-direction: column;
          gap: 0.45rem;
        }
        .ref-scenario-pill {
          width: 100%;
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.55rem 0.65rem;
          border: 2px solid #3d3904;
          border-radius: 10px;
          background: #fffbff;
          font-family: inherit;
          font-weight: 800;
          font-size: 0.82rem;
          color: #3d3904;
          cursor: pointer;
          text-align: left;
          box-shadow: 3px 3px 0 #3d3904;
          transition: transform 0.08s ease, box-shadow 0.08s ease;
        }
        .ref-scenario-pill:hover {
          transform: translate(1px, 1px);
          box-shadow: 2px 2px 0 #3d3904;
        }
        .ref-scenario-pill-active {
          background: #fef3c7;
        }
        .ref-scenario-ico {
          font-size: 1.1rem;
        }

        .ref-premise {
          margin-top: auto;
          font-size: 0.82rem;
          line-height: 1.45;
          color: #4a4420;
        }
        .ref-premise strong {
          display: block;
          margin-top: 0.35rem;
        }

        .ref-main {
          flex: 1;
          position: relative;
          overflow: hidden;
          min-height: 420px;
          background: linear-gradient(180deg, #c9ecff 0%, #eef9ff 42%, #ffffff 72%);
        }

        .ref-cloud {
          position: absolute;
          background: #ffffff;
          border-radius: 50%;
          opacity: 0.92;
          filter: drop-shadow(1px 2px 0 rgba(61, 57, 4, 0.08));
        }
        .ref-cloud-1 {
          width: 120px;
          height: 48px;
          top: 12%;
          left: 8%;
          border-radius: 999px;
        }
        .ref-cloud-2 {
          width: 90px;
          height: 36px;
          top: 18%;
          right: 18%;
          border-radius: 999px;
        }
        .ref-cloud-3 {
          width: 70px;
          height: 28px;
          top: 8%;
          left: 42%;
          border-radius: 999px;
        }

        .ref-hills {
          position: absolute;
          left: 0;
          right: 0;
          bottom: 0;
          height: 28%;
          min-height: 100px;
          background: linear-gradient(180deg, #8bc34a 0%, #6cad3b 40%, #5a9a30 100%);
          border-top: 3px solid #3d3904;
          border-radius: 50% 50% 0 0 / 24px 24px 0 0;
          transform: scaleX(1.15);
        }

        .ref-main-inner {
          position: relative;
          z-index: 2;
          padding: 1.25rem 1rem 2rem;
          display: flex;
          flex-direction: column;
          align-items: center;
          max-width: 720px;
          margin: 0 auto;
        }

        .ref-hero-title {
          margin: 0 0 1rem;
          text-align: center;
          line-height: 1.05;
        }
        .ref-sure {
          display: block;
          font-weight: 900;
          font-size: clamp(2.5rem, 8vw, 4rem);
          color: #cb0319;
          letter-spacing: -0.03em;
        }
        .ref-title-rest {
          display: block;
          font-weight: 900;
          font-size: clamp(1.15rem, 3.5vw, 1.65rem);
          letter-spacing: 0.02em;
          margin-top: 0.15rem;
        }

        .ref-banner-err {
          width: 100%;
          max-width: 28rem;
          padding: 0.6rem 0.75rem;
          border: 2px solid #cb0319;
          border-radius: 10px;
          background: #ffe8e4;
          font-size: 0.85rem;
          font-weight: 700;
          color: #8b0000;
          text-align: center;
        }

        .ref-stage-wrap {
          position: relative;
          width: 100%;
          max-width: 540px;
          margin-bottom: 1.25rem;
        }
        .ref-float-head {
          position: absolute;
          top: -6px;
          right: -4px;
          z-index: 4;
          width: 72px;
          height: 72px;
          border-radius: 50%;
          border: 3px solid #3d3904;
          overflow: hidden;
          background: #fff9e5;
          box-shadow: 4px 4px 0 #3d3904;
        }
        .ref-float-img {
          width: 100%;
          height: 100%;
          object-fit: cover;
          object-position: center top;
          transform: scale(1.15);
        }
        .ref-art-frame {
          border: 3px solid #3d3904;
          border-radius: 16px;
          overflow: hidden;
          background: #f5eb90;
          box-shadow: 6px 6px 0 rgba(61, 57, 4, 0.15);
        }
        .ref-art-img {
          display: block;
          width: 100%;
          height: auto;
        }

        .ref-cta-row {
          display: flex;
          flex-wrap: wrap;
          gap: 1rem;
          justify-content: center;
          width: 100%;
          max-width: 520px;
        }
        .ref-btn-start {
          flex: 1;
          min-width: 140px;
          padding: 0.85rem 1.5rem;
          font-family: inherit;
          font-weight: 900;
          font-size: 1.35rem;
          letter-spacing: 0.06em;
          color: #ffffff;
          background: #cb0319;
          border: 3px solid #3d3904;
          border-radius: 14px;
          cursor: pointer;
          box-shadow: 6px 6px 0 #3d3904;
          transition: transform 0.1s ease, box-shadow 0.1s ease;
        }
        .ref-btn-start:hover {
          transform: translate(2px, 2px);
          box-shadow: 4px 4px 0 #3d3904;
        }
        .ref-btn-start:active {
          transform: translate(4px, 4px);
          box-shadow: 2px 2px 0 #3d3904;
        }
        .ref-btn-achieve {
          flex: 1;
          min-width: 160px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          padding: 0.85rem 1.25rem;
          font-family: inherit;
          font-weight: 900;
          font-size: 1rem;
          letter-spacing: 0.05em;
          color: #ffffff;
          background: #006c95;
          border: 3px solid #3d3904;
          border-radius: 14px;
          text-decoration: none;
          box-shadow: 6px 6px 0 #3d3904;
          transition: transform 0.1s ease, box-shadow 0.1s ease;
        }
        .ref-btn-achieve:hover {
          transform: translate(2px, 2px);
          box-shadow: 4px 4px 0 #3d3904;
          color: #ffffff;
        }
        .ref-btn-achieve:active {
          transform: translate(4px, 4px);
          box-shadow: 2px 2px 0 #3d3904;
        }
        .ref-medal {
          display: grid;
          place-items: center;
          width: 2rem;
          height: 2rem;
          border-radius: 50%;
          background: linear-gradient(145deg, #ffd76a, #f2a900);
          border: 2px solid #3d3904;
          font-size: 1rem;
        }

        @media (max-width: 899px) {
          .ref-sidebar {
            border-right: none;
            border-bottom: 3px solid #3d3904;
          }
          .ref-scenario-list {
            flex-direction: row;
            flex-wrap: wrap;
          }
          .ref-scenario-pill {
            width: auto;
            flex: 1 1 auto;
            min-width: 140px;
          }
        }
      `}</style>
    </div>
  );
}
