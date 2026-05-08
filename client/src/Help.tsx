import { Link } from "react-router-dom";
import { theme } from "./theme";

export function Help() {
  return (
    <div style={{ maxWidth: 640, margin: "0 auto", padding: "1.5rem", lineHeight: 1.55 }}>
      <nav style={{ marginBottom: "1rem" }}>
        <Link to="/" style={{ color: theme.secondary, fontWeight: 800 }}>
          ← Home
        </Link>
      </nav>
      <h1 style={{ marginTop: 0 }}>Help</h1>
      <p>
        Pick a scenario, choose responses, and watch the narrator stream back. Neural score updates server-side;
        run ends after four beats.
      </p>
      <p>
        Offline dev: run the FastAPI server so <code>/api</code> resolves (or set API base in Settings).
      </p>
    </div>
  );
}
