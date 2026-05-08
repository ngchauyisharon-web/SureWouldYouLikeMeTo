import { Link } from "react-router-dom";
import { theme } from "./theme";

const ARCHIVE_KEY = "sure_archives_v1";

export function Archives() {
  let rows: { slug: string; title: string; score: number; achievement?: string | null; at?: string }[] =
    [];
  try {
    const raw = globalThis.localStorage.getItem(ARCHIVE_KEY);
    rows = raw ? JSON.parse(raw) : [];
  } catch {
    rows = [];
  }

  return (
    <div style={{ maxWidth: 640, margin: "0 auto", padding: "1.5rem" }}>
      <nav style={{ marginBottom: "1rem" }}>
        <Link to="/" style={{ color: theme.secondary, fontWeight: 800 }}>
          ← Home
        </Link>
      </nav>
      <h1 style={{ marginTop: 0 }}>Archives</h1>
      {rows.length === 0 ? (
        <p>Nothing archived yet — finish a run on the play screen.</p>
      ) : (
        <ul style={{ paddingLeft: "1.1rem", lineHeight: 1.6 }}>
          {rows.map((r, i) => (
            <li key={i}>
              <strong>{r.title}</strong> — score {r.score}
              {r.achievement ? ` — ★ ${r.achievement}` : ""}
              {r.at ? ` (${r.at})` : ""}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
