from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class TurnDef:
    id: int
    choices: list[str]
    score_delta_by_choice: list[int]
    static_line: str | None


@dataclass(frozen=True)
class ScenarioDef:
    slug: str
    title: str
    icon: str
    tagline: str
    body: str
    turns: list[TurnDef]


def _repo_shared_path() -> Path:
    return Path(__file__).resolve().parents[2] / "shared" / "scenarios.json"


@lru_cache
def load_scenarios() -> tuple[dict, dict[str, ScenarioDef]]:
    path = _repo_shared_path()
    raw = json.loads(path.read_text(encoding="utf-8"))
    by_slug: dict[str, ScenarioDef] = {}
    for s in raw["scenarios"]:
        turns = []
        for t in s["turns"]:
            turns.append(
                TurnDef(
                    id=int(t["id"]),
                    choices=list(t["choices"]),
                    score_delta_by_choice=list(t["score_delta_by_choice"]),
                    static_line=t.get("static_line"),
                )
            )
        by_slug[s["slug"]] = ScenarioDef(
            slug=s["slug"],
            title=s["title"],
            icon=s["icon"],
            tagline=s["tagline"],
            body=s["body"],
            turns=turns,
        )
    return raw, by_slug


def get_scenario(slug: str) -> ScenarioDef | None:
    _, by_slug = load_scenarios()
    return by_slug.get(slug)


def list_scenario_summaries() -> list[dict]:
    _, by_slug = load_scenarios()
    return [
        {
            "slug": s.slug,
            "title": s.title,
            "icon": s.icon,
            "tagline": s.tagline,
            "body": s.body,
        }
        for s in by_slug.values()
    ]
