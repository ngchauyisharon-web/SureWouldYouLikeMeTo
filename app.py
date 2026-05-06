"""
Satirical Cutout — Streamlit landing page (landing only; gameplay page is a placeholder hook).
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

# -----------------------------------------------------------------------------
# Paths & asset placeholders (swap files under assets/ when artwork is ready)
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
ROBOT_IMG = ASSETS_DIR / "robot.png"
PLAYER_IMG = ASSETS_DIR / "player.png"

# Palette (design system)
C_PRIMARY = "#cb0319"
C_SECONDARY = "#006c95"
C_TERTIARY = "#4c6f00"
C_SURFACE = "#fffbff"
C_SURFACE_LOW = "#fff9e5"
C_SURFACE_HIGH = "#f5eb90"
C_OUTLINE = "#c3bb7a"
C_ON_SURFACE = "#3d3904"

SCENARIO_COPY: dict[str, dict[str, str]] = {
    "AI Overuse": {
        "tagline": "Too many drafts, too little shame.",
        "body": "Metrics demand velocity. Your neural partner suggests twelve more variants before lunch.",
    },
    "Hallucination": {
        "tagline": "Confidence is high. Accuracy is negotiable.",
        "body": "Facts assemble themselves from vibes. Hold the clipboard steady while reality negotiates.",
    },
    "Ethics": {
        "tagline": "The trolley has a Terms of Service update.",
        "body": "Principles enter the chat. Stakeholders bring slide decks. You bring the uncomfortable questions.",
    },
}

# Stable slugs for button keys + CSS hooks (avoid spaces/special chars in keys)
SCENARIO_SLUGS: dict[str, str] = {
    "AI Overuse": "ai_overuse",
    "Hallucination": "hallucination",
    "Ethics": "ethics",
}

SCENARIO_ICONS: dict[str, str] = {
    "AI Overuse": "⚡",
    "Hallucination": "✨",
    "Ethics": "⚖️",
}


def _init_session_state() -> None:
    if "scenario" not in st.session_state:
        st.session_state.scenario = "AI Overuse"
    if "game_starting" not in st.session_state:
        st.session_state.game_starting = False
    if "show_achievements" not in st.session_state:
        st.session_state.show_achievements = False
    if "nav_active" not in st.session_state:
        st.session_state.nav_active = "Play"


def _inject_theme_css() -> None:
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800;900&display=swap');

:root {{
  --cutout-primary: {C_PRIMARY};
  --cutout-primary-soft: #e4253a;
  --cutout-secondary: {C_SECONDARY};
  --cutout-tertiary: {C_TERTIARY};
  --cutout-surface: {C_SURFACE};
  --cutout-surface-low: {C_SURFACE_LOW};
  --cutout-surface-high: {C_SURFACE_HIGH};
  --cutout-outline: {C_OUTLINE};
  --cutout-on-surface: {C_ON_SURFACE};
  --cutout-shadow: color-mix(in srgb, {C_ON_SURFACE} 22%, transparent);
  --cutout-font: 'Plus Jakarta Sans', system-ui, sans-serif;
}}

.stApp, .stMarkdown, button, h1, h2, h3, p, span {{
  font-family: var(--cutout-font), system-ui, sans-serif !important;
}}

/* App chrome: warm paper field */
.stApp {{
  background: radial-gradient(1200px 800px at 15% -10%, {C_SURFACE_LOW} 0%, transparent 55%),
    radial-gradient(900px 600px at 100% 10%, color-mix(in srgb, {C_SECONDARY} 12%, transparent) 0%, transparent 50%),
    {C_SURFACE} !important;
}}

/* Main block: breathing room */
.block-container {{
  padding-top: 1.25rem !important;
  padding-bottom: 2rem !important;
  max-width: 1200px !important;
}}

header[data-testid="stHeader"] {{
  background: transparent !important;
}}

/* Landing uses custom columns — hide default Streamlit sidebar chrome */
section[data-testid="stSidebar"] {{
  display: none !important;
}}
div[data-testid="collapsedControl"] {{
  display: none !important;
}}

/* Top nav glass strip */
.cutout-topnav {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.65rem 1.1rem;
  margin-bottom: 1.25rem;
  border-radius: 14px;
  background: color-mix(in srgb, var(--cutout-surface-low) 78%, transparent);
  border: 1px solid color-mix(in srgb, var(--cutout-outline) 35%, transparent);
  box-shadow: 0 10px 28px var(--cutout-shadow);
  backdrop-filter: blur(10px);
}}

.cutout-brand {{
  font-weight: 900;
  font-style: italic;
  letter-spacing: -0.03em;
  font-size: clamp(0.85rem, 1.6vw, 1rem);
  color: var(--cutout-primary);
  text-shadow: 2px 3px 0 color-mix(in srgb, var(--cutout-on-surface) 14%, transparent);
  max-width: min(340px, 42vw);
  line-height: 1.05;
}}

.cutout-nav-cluster {{
  display: flex;
  align-items: center;
  gap: clamp(0.35rem, 2vw, 1.25rem);
  flex-wrap: wrap;
  justify-content: flex-end;
}}

.cutout-nav-link {{
  font-weight: 800;
  font-size: 0.82rem;
  letter-spacing: 0.06em;
  color: var(--cutout-on-surface);
  opacity: 0.85;
  padding-bottom: 2px;
  border-bottom: 3px solid transparent;
  cursor: default;
  user-select: none;
}}

.cutout-nav-link.active {{
  color: var(--cutout-primary);
  border-bottom-color: color-mix(in srgb, var(--cutout-primary) 85%, white);
}}

.cutout-help {{
  font-weight: 700;
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  color: var(--cutout-secondary);
}}

.cutout-avatar {{
  width: 38px;
  height: 38px;
  border-radius: 999px;
  background: linear-gradient(145deg, var(--cutout-surface-high), var(--cutout-surface-low));
  border: 2px solid color-mix(in srgb, var(--cutout-outline) 55%, transparent);
  box-shadow: 0 8px 18px var(--cutout-shadow), inset 0 1px 0 rgba(255,255,255,0.65);
  display: grid;
  place-items: center;
  font-weight: 900;
  font-size: 0.72rem;
  color: var(--cutout-on-surface);
}}

/*
  Sidebar panel — only the top split row's first column (not nested column grids).
  Streamlit nests further `stHorizontalBlock` rows inside the hero column for CTAs etc.
*/
.block-container div[data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:first-child > div[data-testid="stVerticalBlock"] {{
  background: linear-gradient(180deg,
    color-mix(in srgb, var(--cutout-surface-low) 92%, transparent),
    color-mix(in srgb, var(--cutout-surface) 96%, transparent));
  border-radius: 18px;
  padding: 1.15rem 1rem 1.25rem;
  border: 1px solid color-mix(in srgb, var(--cutout-outline) 38%, transparent);
  box-shadow: 0 18px 36px var(--cutout-shadow);
  transform: rotate(-0.35deg);
}}

.cutout-status {{
  display: flex;
  gap: 0.65rem;
  align-items: flex-start;
  padding: 0.75rem 0.85rem;
  border-radius: 14px;
  background: color-mix(in srgb, var(--cutout-primary) 8%, var(--cutout-surface));
  border: 1px solid color-mix(in srgb, var(--cutout-primary) 22%, transparent);
  margin-bottom: 1rem;
}}

.cutout-brain {{
  font-size: 1.35rem;
  line-height: 1;
  filter: drop-shadow(0 4px 6px var(--cutout-shadow));
}}

.cutout-status-title {{
  font-weight: 900;
  letter-spacing: 0.04em;
  font-size: 0.72rem;
  text-transform: uppercase;
  color: var(--cutout-on-surface);
  margin: 0 0 0.15rem 0;
}}

.cutout-status-meta {{
  margin: 0;
  font-size: 0.86rem;
  font-weight: 700;
  color: var(--cutout-secondary);
}}

.cutout-scenario-list {{
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}}

/* Scenario pickers — keys: scenario_<slug> → class st-key-scenario_<slug> on wrapper */
[class*="st-key-scenario_"] button {{
  width: 100%;
  justify-content: flex-start !important;
  text-align: left !important;
  border-radius: 14px !important;
  padding: 0.7rem 0.85rem !important;
  font-weight: 800 !important;
  letter-spacing: 0.02em !important;
  border: 2px solid color-mix(in srgb, var(--cutout-outline) 45%, transparent) !important;
  background: color-mix(in srgb, var(--cutout-surface) 90%, transparent) !important;
  color: var(--cutout-on-surface) !important;
  box-shadow: 0 10px 0 color-mix(in srgb, var(--cutout-on-surface) 12%, transparent) !important;
  transition: transform 0.08s ease, box-shadow 0.12s ease, background 0.12s ease !important;
}}

[class*="st-key-scenario_"] button:hover {{
  transform: translateY(-1px) !important;
  box-shadow: 0 14px 0 color-mix(in srgb, var(--cutout-on-surface) 14%, transparent) !important;
}}

[class*="st-key-scenario_"] button:active {{
  transform: translateY(3px) !important;
  box-shadow: 0 6px 0 color-mix(in srgb, var(--cutout-on-surface) 14%, transparent) !important;
}}

.cutout-premise {{
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid color-mix(in srgb, var(--cutout-outline) 28%, transparent);
}}

.cutout-premise p {{
  font-size: 0.92rem;
  line-height: 1.45;
  color: var(--cutout-on-surface);
  opacity: 0.92;
  margin: 0;
}}

/* Hero stage */
.cutout-hero-wrap {{
  position: relative;
}}

.cutout-hero-stage {{
  position: relative;
  border-radius: 22px;
  padding: clamp(1rem, 3vw, 1.65rem);
  background: linear-gradient(180deg,
    color-mix(in srgb, var(--cutout-secondary) 14%, var(--cutout-surface-low)),
    color-mix(in srgb, var(--cutout-tertiary) 12%, var(--cutout-surface)));
  border: 1px solid color-mix(in srgb, var(--cutout-outline) 35%, transparent);
  box-shadow:
    0 26px 50px var(--cutout-shadow),
    inset 0 1px 0 rgba(255,255,255,0.65);
  transform: rotate(0.45deg);
  overflow: hidden;
}}

.cutout-cloud {{
  position: absolute;
  border-radius: 999px;
  background: rgba(255,255,255,0.88);
  filter: blur(0.2px);
  box-shadow: 0 14px 30px color-mix(in srgb, var(--cutout-secondary) 18%, transparent);
  opacity: 0.95;
}}

.cutout-cloud.c1 {{ width: 120px; height: 52px; top: 14%; left: 8%; }}
.cutout-cloud.c2 {{ width: 90px; height: 40px; top: 22%; left: 42%; }}
.cutout-cloud.c3 {{ width: 140px; height: 58px; top: 10%; right: 12%; }}

.cutout-hill {{
  position: absolute;
  bottom: -40px;
  width: 120%;
  left: -10%;
  height: 120px;
  border-radius: 50%;
  background: radial-gradient(circle at 50% 0%, color-mix(in srgb, var(--cutout-tertiary) 92%, black) 0%, var(--cutout-tertiary) 55%, color-mix(in srgb, var(--cutout-tertiary) 70%, var(--cutout-on-surface)) 100%);
  opacity: 0.95;
  box-shadow: 0 -16px 40px var(--cutout-shadow);
}}

.cutout-headline {{
  position: relative;
  z-index: 2;
  margin: 0 0 0.5rem 0;
  line-height: 0.92;
  letter-spacing: -0.045em;
  font-weight: 900;
  font-size: clamp(1.85rem, 5.2vw, 3.15rem);
  text-transform: uppercase;
}}

.cutout-headline .blood {{
  color: var(--cutout-primary);
  text-shadow:
    3px 4px 0 rgba(255,255,255,0.92),
    6px 8px 24px color-mix(in srgb, var(--cutout-primary) 35%, transparent);
}}

.cutout-headline .ink {{
  color: var(--cutout-on-surface);
  text-shadow: 3px 4px 0 rgba(255,255,255,0.75);
}}

.cutout-hero-sub {{
  position: relative;
  z-index: 2;
  font-weight: 800;
  font-size: clamp(0.95rem, 2.1vw, 1.15rem);
  color: var(--cutout-on-surface);
  margin: 0.35rem 0 1rem 0;
  max-width: 46ch;
}}

.cutout-stage-panel {{
  position: relative;
  z-index: 2;
  margin-top: 0.5rem;
  border-radius: 18px;
  padding: 0.85rem;
  background: color-mix(in srgb, var(--cutout-surface-low) 55%, transparent);
  border: 1px solid color-mix(in srgb, var(--cutout-outline) 30%, transparent);
  box-shadow: 0 16px 34px var(--cutout-shadow);
}}

.cutout-char-row {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
  align-items: end;
}}

@media (max-width: 900px) {{
  .cutout-char-row {{
    grid-template-columns: 1fr;
  }}
  .cutout-brand {{
    max-width: unset;
  }}
}}

.cutout-art {{
  border-radius: 16px;
  padding: 0.6rem;
  background: linear-gradient(180deg, rgba(255,255,255,0.72), rgba(255,255,255,0.42));
  border: 2px solid rgba(255,255,255,0.85);
  box-shadow:
    0 14px 0 color-mix(in srgb, var(--cutout-on-surface) 12%, transparent),
    0 22px 38px var(--cutout-shadow);
  min-height: 180px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
}}

.cutout-art-label {{
  font-size: 0.68rem;
  font-weight: 900;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--cutout-secondary);
  margin-bottom: 0.35rem;
}}

.placeholder-art {{
  width: 100%;
  flex: 1;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-weight: 900;
  letter-spacing: 0.06em;
  color: var(--cutout-on-surface);
  border: 2px dashed color-mix(in srgb, var(--cutout-outline) 55%, transparent);
  background: color-mix(in srgb, var(--cutout-surface-high) 35%, white);
}}

.placeholder-art.robot-ph {{
  background:
    radial-gradient(circle at 30% 30%, color-mix(in srgb, var(--cutout-secondary) 25%, transparent), transparent 55%),
    color-mix(in srgb, var(--cutout-surface-high) 25%, white);
}}

.placeholder-art.player-ph {{
  background:
    radial-gradient(circle at 70% 25%, color-mix(in srgb, var(--cutout-primary) 18%, transparent), transparent 50%),
    color-mix(in srgb, var(--cutout-surface-low) 45%, white);
}}

.cutout-float-badge {{
  position: absolute;
  top: 10px;
  right: 12px;
  width: 64px;
  height: 64px;
  border-radius: 999px;
  background: white;
  border: 3px solid rgba(255,255,255,0.95);
  box-shadow: 0 14px 28px var(--cutout-shadow);
  display: grid;
  place-items: center;
  font-size: 1.6rem;
  transform: rotate(8deg);
  z-index: 4;
}}

/* CTA row */
.cutout-cta-row {{
  display: flex;
  flex-wrap: wrap;
  gap: 0.85rem;
  align-items: center;
  margin-top: 1.15rem;
  position: relative;
  z-index: 3;
}}

/* CTA buttons — keys cta_start / cta_achievements */
.st-key-cta_start button {{
  background: linear-gradient(180deg, var(--cutout-primary-soft), var(--cutout-primary)) !important;
  color: white !important;
  border: 3px solid rgba(255,255,255,0.92) !important;
  border-radius: 999px !important;
  padding: 0.85rem 2.6rem !important;
  font-weight: 900 !important;
  letter-spacing: 0.16em !important;
  font-size: 0.95rem !important;
  box-shadow:
    0 14px 0 color-mix(in srgb, var(--cutout-primary) 55%, black),
    0 22px 44px color-mix(in srgb, var(--cutout-primary) 35%, transparent) !important;
  transition: transform 0.08s ease, filter 0.12s ease, box-shadow 0.12s ease !important;
}}

.st-key-cta_start button:hover {{
  filter: brightness(1.03);
  transform: translateY(-2px) !important;
}}

.st-key-cta_start button:active {{
  transform: translateY(4px) !important;
  box-shadow:
    0 7px 0 color-mix(in srgb, var(--cutout-primary) 55%, black),
    0 14px 28px color-mix(in srgb, var(--cutout-primary) 35%, transparent) !important;
}}

.st-key-cta_achievements button {{
  background: linear-gradient(180deg,
    color-mix(in srgb, var(--cutout-secondary) 92%, white),
    var(--cutout-secondary)) !important;
  color: white !important;
  border-radius: 999px !important;
  padding: 0.78rem 1.9rem !important;
  font-weight: 900 !important;
  letter-spacing: 0.12em !important;
  border: 3px solid rgba(255,255,255,0.85) !important;
  box-shadow:
    0 12px 0 color-mix(in srgb, var(--cutout-secondary) 55%, black),
    0 18px 36px color-mix(in srgb, var(--cutout-secondary) 30%, transparent) !important;
}}

.st-key-cta_achievements button:hover {{
  filter: brightness(1.04);
  transform: translateY(-1px) !important;
}}

.st-key-cta_achievements button:active {{
  transform: translateY(3px) !important;
}}

.cutout-ach-wrap {{
  position: relative;
}}

.cutout-ach-badge {{
  position: absolute;
  left: -6px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 2;
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: linear-gradient(145deg, #ffd76a, #f2a900);
  border: 2px solid rgba(255,255,255,0.95);
  box-shadow: 0 10px 22px var(--cutout-shadow);
  display: grid;
  place-items: center;
  font-size: 1rem;
}}

/* Achievements overlay panel */
.cutout-modal {{
  margin-top: 1rem;
  padding: 1rem 1.1rem;
  border-radius: 16px;
  background: color-mix(in srgb, var(--cutout-surface) 92%, transparent);
  border: 1px solid color-mix(in srgb, var(--cutout-outline) 40%, transparent);
  box-shadow: 0 22px 50px var(--cutout-shadow);
}}

.cutout-modal h3 {{
  margin: 0 0 0.35rem 0;
  font-size: 0.78rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--cutout-secondary);
}}

.cutout-modal p {{
  margin: 0;
  color: var(--cutout-on-surface);
  line-height: 1.45;
}}

.cutout-start-banner {{
  margin-top: 0.85rem;
  padding: 0.75rem 0.95rem;
  border-radius: 14px;
  background: color-mix(in srgb, var(--cutout-primary) 12%, white);
  border: 1px solid color-mix(in srgb, var(--cutout-primary) 25%, transparent);
  color: var(--cutout-on-surface);
  font-weight: 700;
}}

/* Responsive layout columns */
@media (max-width: 860px) {{
  .block-container div[data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:first-child > div[data-testid="stVerticalBlock"] {{
    transform: none;
    margin-bottom: 1rem;
  }}
  .cutout-hero-stage {{
    transform: none;
  }}
}}
</style>
""",
        unsafe_allow_html=True,
    )


def _inject_scenario_selection_css(selected_label: str) -> None:
    """Highlight the active scenario button (warm yellow stack) over base styles."""
    slug = SCENARIO_SLUGS[selected_label]
    st.markdown(
        f"""
<style>
.st-key-scenario_{slug} button {{
  background: linear-gradient(180deg,
    var(--cutout-surface-high),
    color-mix(in srgb, var(--cutout-surface-high) 88%, var(--cutout-outline))) !important;
  border-color: color-mix(in srgb, var(--cutout-outline) 65%, transparent) !important;
}}
</style>
""",
        unsafe_allow_html=True,
    )


def _render_top_nav() -> None:
    active = st.session_state.nav_active
    st.markdown(
        f"""
<div class="cutout-topnav">
  <div class="cutout-brand">SURE! WOULD YOU LIKE ME TO…?</div>
  <div class="cutout-nav-cluster">
    <span class="cutout-nav-link {'active' if active == 'Play' else ''}">PLAY</span>
    <span class="cutout-nav-link {'active' if active == 'Archives' else ''}">ARCHIVES</span>
    <span class="cutout-nav-link {'active' if active == 'Settings' else ''}">SETTINGS</span>
    <span class="cutout-help">HELP</span>
    <div class="cutout-avatar" aria-hidden="true">YOU</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_sidebar_column() -> None:
    """Left column: system status + scenario chips + premise."""
    st.markdown(
        """
<div class="cutout-status">
  <div class="cutout-brain" aria-hidden="true">🧠</div>
  <div>
    <p class="cutout-status-title">Neural Scoring</p>
    <p class="cutout-status-meta">Current state: Smoothing</p>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="cutout-scenario-list">', unsafe_allow_html=True)
    for name in SCENARIO_COPY:
        slug = SCENARIO_SLUGS[name]
        icon = SCENARIO_ICONS.get(name, "•")
        label = f"{icon}  {name}"
        if st.button(
            label,
            key=f"scenario_{slug}",
            type="secondary",
            use_container_width=True,
        ):
            st.session_state.scenario = name
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        """
<div class="cutout-premise">
  <p>
    AI is taking over, hallucinating, and making questionable choices.
    <strong>Which disaster would you like to manage today?</strong>
  </p>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_illustration_zone() -> None:
    """Robot + player art with file fallback to cutout placeholders."""
    st.markdown('<div class="cutout-stage-panel">', unsafe_allow_html=True)
    st.markdown('<div class="cutout-float-badge" title="Player reaction">😑</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            '<div class="cutout-art"><div class="cutout-art-label">Friendly overkill</div>',
            unsafe_allow_html=True,
        )
        if ROBOT_IMG.exists():
            st.image(str(ROBOT_IMG), use_container_width=True)
        else:
            st.markdown(
                '<div class="placeholder-art robot-ph">ROBOT / AI<br/><span style="font-size:0.65rem;font-weight:800;opacity:.55">assets/robot.png</span></div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown(
            '<div class="cutout-art"><div class="cutout-art-label">Human skeptic</div>',
            unsafe_allow_html=True,
        )
        if PLAYER_IMG.exists():
            st.image(str(PLAYER_IMG), use_container_width=True)
        else:
            st.markdown(
                '<div class="placeholder-art player-ph">PLAYER<br/><span style="font-size:0.65rem;font-weight:800;opacity:.55">assets/player.png</span></div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def _render_hero_column() -> None:
    scenario = st.session_state.scenario
    copy = SCENARIO_COPY[scenario]

    st.markdown('<div class="cutout-hero-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="cutout-hero-stage">', unsafe_allow_html=True)

    # Layered scene
    st.markdown(
        '<div class="cutout-cloud c1"></div><div class="cutout-cloud c2"></div><div class="cutout-cloud c3"></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="cutout-hill"></div>', unsafe_allow_html=True)

    st.markdown(
        """
<h1 class="cutout-headline">
  <span class="blood">SURE!</span><br/>
  <span class="ink">WOULD YOU LIKE ME TO…?</span>
</h1>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<p class="cutout-hero-sub"><strong>{scenario}</strong> — {copy["tagline"]}<br/>{copy["body"]}</p>',
        unsafe_allow_html=True,
    )

    _render_illustration_zone()

    # CTAs
    cta_a, cta_b = st.columns([1.15, 1], gap="medium")
    with cta_a:
        if st.button("START", key="cta_start", type="primary", use_container_width=False):
            st.session_state.game_starting = True
            # --- Future gameplay hook: create `pages/game.py` then uncomment ---
            # st.switch_page("pages/game.py")
            # ------------------------------------------------------------------

    with cta_b:
        st.markdown('<div class="cutout-ach-wrap">', unsafe_allow_html=True)
        st.markdown('<div class="cutout-ach-badge" title="Achievement ribbon">★</div>', unsafe_allow_html=True)
        if st.button("ACHIEVEMENTS", key="cta_achievements", type="secondary", use_container_width=True):
            st.session_state.show_achievements = not st.session_state.show_achievements
        st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.game_starting:
        st.markdown(
            '<div class="cutout-start-banner">Game starting… (placeholder — wire <code>st.switch_page</code> when the play page exists.)</div>',
            unsafe_allow_html=True,
        )

    if st.session_state.show_achievements:
        st.markdown(
            """
<div class="cutout-modal">
  <h3>Achievements</h3>
  <p>
    Nothing unlocked yet — your conscience is still installing updates.
    Replace this panel with real trophies when progression exists.
  </p>
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(
        page_title="SURE! — Satirical Cutout",
        page_icon="✂️",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    _init_session_state()
    _inject_theme_css()
    _inject_scenario_selection_css(st.session_state.scenario)

    _render_top_nav()

    # Sidebar / main split (not Streamlit sidebar — asymmetric columns)
    left_w = 0.92
    gap = "large"
    col_side, col_hero = st.columns([left_w, 2.25], gap=gap)

    with col_side:
        _render_sidebar_column()

    with col_hero:
        _render_hero_column()


if __name__ == "__main__":
    main()
