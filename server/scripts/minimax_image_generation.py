"""
Call MiniMax image-01 with a reference image (URL or local file as data URL).

Usage (from the `server/` directory, with `.env` containing MINIMAX_API_KEY):

  pip install -r requirements-dev.txt
  python scripts/minimax_image_generation.py

Default reference: `scripts/references/south-park-style-reference.png` when that file exists.
Otherwise `MINIMAX_SUBJECT_IMAGE_URL`, then the MiniMax CDN demo URL.

MiniMax OpenAPI documents `subject_reference[].type` as only `character` (portrait-oriented).
For a *style* reference (e.g. cutout / paper-doll look), we still use `character` and strengthen
the prompt so the model follows the reference's art language, not a specific person's identity.

Outputs `output-0.jpeg`, … next to this script (gitignored).
"""
from __future__ import annotations

import base64
import mimetypes
import os
import sys
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv

    _env = Path(__file__).resolve().parent.parent / ".env"
    if _env.is_file():
        load_dotenv(_env)
except ImportError:
    pass

URL = "https://api.minimax.io/v1/image_generation"
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_LOCAL_REFERENCE = SCRIPT_DIR / "references" / "south-park-style-reference.png"
DEFAULT_SUBJECT_URL = (
    "https://cdn.hailuoai.com/prod/2025-08-12-17/video_cover/"
    "1754990600020238321-411603868533342214-cover.jpg"
)

# Prompt tuned for “style like reference” (flat cutout animation) rather than copying characters.
DEFAULT_STYLE_PROMPT = (
    "A girl stands by the library window, gazing into the distance. "
    "Render in the same visual style as the reference image: simple 2D cutout / paper-doll "
    "animation look, bold black outlines, flat saturated colors, minimal shading, "
    "geometric shapes, snowy daylight mood outside the window — do not depict the reference "
    "characters; only the new scene and style."
)


def _mime_for_path(p: Path) -> str:
    guessed, _ = mimetypes.guess_type(p.name)
    if guessed:
        return guessed
    suf = p.suffix.lower()
    if suf == ".png":
        return "image/png"
    if suf in (".jpg", ".jpeg"):
        return "image/jpeg"
    return "application/octet-stream"


def resolve_image_file() -> str:
    """Public URL or data URL per MiniMax `image_file` field."""
    override = os.environ.get("MINIMAX_REFERENCE_IMAGE_PATH", "").strip()
    if override:
        path = Path(override)
        if not path.is_absolute():
            path = (SCRIPT_DIR.parent / path).resolve()
    else:
        path = DEFAULT_LOCAL_REFERENCE
    if override and not path.is_file():
        print(f"MINIMAX_REFERENCE_IMAGE_PATH not found: {path}", file=sys.stderr)
        sys.exit(1)
    if path.is_file():
        raw = path.read_bytes()
        if len(raw) > 10 * 1024 * 1024:
            print("Reference image must be under 10MB per MiniMax docs.", file=sys.stderr)
            sys.exit(1)
        b64 = base64.standard_b64encode(raw).decode("ascii")
        mime = _mime_for_path(path)
        return f"data:{mime};base64,{b64}"

    subject_url = os.environ.get("MINIMAX_SUBJECT_IMAGE_URL", "").strip() or DEFAULT_SUBJECT_URL
    return subject_url


def main() -> None:
    api_key = os.environ.get("MINIMAX_API_KEY", "").strip()
    if not api_key:
        print("Set MINIMAX_API_KEY in server/.env (see .env.example).", file=sys.stderr)
        sys.exit(1)

    ref_type = os.environ.get("MINIMAX_SUBJECT_REFERENCE_TYPE", "character").strip() or "character"
    if ref_type != "character":
        print(
            'MiniMax currently documents only type "character" for subject_reference; '
            f'ignoring MINIMAX_SUBJECT_REFERENCE_TYPE={ref_type!r} and using "character".',
            file=sys.stderr,
        )
        ref_type = "character"

    prompt = os.environ.get("MINIMAX_PROMPT", "").strip() or DEFAULT_STYLE_PROMPT
    image_file = resolve_image_file()

    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": "image-01",
        "prompt": prompt,
        "aspect_ratio": os.environ.get("MINIMAX_ASPECT_RATIO", "16:9").strip() or "16:9",
        "subject_reference": [
            {
                "type": "character",
                "image_file": image_file,
            }
        ],
        "response_format": "base64",
    }

    response = requests.post(URL, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    body = response.json()
    images = body["data"]["image_base64"]

    for i in range(len(images)):
        out_path = SCRIPT_DIR / f"output-{i}.jpeg"
        out_path.write_bytes(base64.b64decode(images[i]))
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
