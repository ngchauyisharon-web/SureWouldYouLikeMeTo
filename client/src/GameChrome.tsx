import type { ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import type { ScenarioSummary } from "./api";

type Props = {
  scenarios: ScenarioSummary[];
  /** Highlights which scenario is active in the main flow; sidebar pills are display-only. */
  selectedSlug: string;
  error?: string | null;
  children: ReactNode;
};

/** PLAY nav highlight on splash (/) and topic selection (/topics). */
export function GameChrome({ scenarios, selectedSlug, error, children }: Props) {
  const { pathname } = useLocation();
  const playHighlighted = pathname === "/" || pathname === "/topics";

  return (
    <div className="ref-landing">
      <header className="ref-topnav">
        <div className="ref-topnav-inner">
          <span className="ref-logo">SURE! WOULD YOU LIKE ME TO...?</span>
          <nav className="ref-topnav-center" aria-label="Main">
            <NavLink to="/" end className={`ref-top-link ${playHighlighted ? "ref-top-link-active" : ""}`}>
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

          {error ? <p className="ref-sidebar-err">{error}</p> : null}

          <ul className="ref-scenario-list" aria-label="Scenario themes (display only)">
            {scenarios.map((s) => (
              <li key={s.slug}>
                <div className="ref-scenario-pill" aria-current={selectedSlug === s.slug ? "true" : undefined}>
                  <span className="ref-scenario-ico" aria-hidden>
                    {s.icon}
                  </span>
                  {s.title}
                </div>
              </li>
            ))}
          </ul>

          <p className="ref-premise">
            AI is taking over, hallucinating, and making questionable choices.{" "}
            <strong>Which disaster would you like to manage today?</strong>
          </p>
        </aside>

        {children}
      </div>

      <style>{CHROME_CSS}</style>
    </div>
  );
}

const CHROME_CSS = `
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
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 1rem;
          padding: 0.65rem clamp(0.75rem, 2vw, 1.5rem);
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
          width: 100%;
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
            width: 312px;
            flex-shrink: 0;
          }
        }

        .ref-sidebar-err {
          margin: 0;
          padding: 0.5rem 0.55rem;
          border-radius: 8px;
          background: #ffe8e4;
          border: 2px solid #cb0319;
          font-size: 0.72rem;
          font-weight: 700;
          color: #8b0000;
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
          padding: 0.825rem 0.65rem;
          border: 2px solid #3d3904;
          border-radius: 10px;
          background: #fffbff;
          font-family: inherit;
          font-weight: 800;
          font-size: 0.82rem;
          color: #3d3904;
          cursor: default;
          text-align: left;
          box-shadow: 3px 3px 0 #3d3904;
          user-select: none;
        }
        .ref-scenario-ico {
          font-size: 1.65rem;
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
`;
