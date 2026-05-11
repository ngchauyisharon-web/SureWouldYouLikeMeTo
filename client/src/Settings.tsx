import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { theme } from "./theme";

const API_KEY = "sure_api_base";

export function Settings() {
  const [base, setBase] = useState("");

  useEffect(() => {
    setBase(globalThis.localStorage.getItem(API_KEY) ?? "");
  }, []);

  const save = () => {
    globalThis.localStorage.setItem(API_KEY, base.trim());
    globalThis.dispatchEvent(new Event("sure-settings"));
  };

  return (
    <div style={{ maxWidth: 560, margin: "0 auto", padding: "1.5rem" }}>
      <nav style={{ marginBottom: "1rem" }}>
        <Link to="/" style={{ color: theme.secondary, fontWeight: 800 }}>
          ← Home
        </Link>
      </nav>
      <h1 style={{ marginTop: 0 }}>Settings</h1>
      <p style={{ lineHeight: 1.5 }}>
        Override API base URL (include protocol, no trailing slash). Leave empty to use the value from the
        production build (<code>VITE_API_BASE</code>) or same-origin <code>/api</code> in Vite dev.
      </p>
      <input
        value={base}
        onChange={(e) => setBase(e.target.value)}
        placeholder="https://api.example.com"
        style={{
          width: "100%",
          padding: "0.65rem 0.75rem",
          borderRadius: 10,
          border: `2px solid color-mix(in srgb, ${theme.outline} 55%, transparent)`,
          fontFamily: "inherit",
          marginBottom: "0.75rem",
        }}
      />
      <button
        type="button"
        onClick={save}
        style={{
          padding: "0.55rem 1.2rem",
          borderRadius: 999,
          fontWeight: 800,
          border: "none",
          background: theme.secondary,
          color: "white",
          cursor: "pointer",
        }}
      >
        Save
      </button>
    </div>
  );
}
