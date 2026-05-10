"""MiniMax image_generation JSON parsing and prompt length (no live API)."""

from app.image_gen import MINIMAX_PROMPT_MAX, _full_image_prompt, parse_minimax_image_payload


def test_parse_minimax_success_base64() -> None:
    data = {
        "base_resp": {"status_code": 0, "status_msg": "success"},
        "data": {"image_base64": ["YmFzZTY0X3N0dWI="]},
    }
    b64, err, url = parse_minimax_image_payload(data)
    assert b64 == "YmFzZTY0X3N0dWI="
    assert err is None
    assert url is None


def test_parse_minimax_auth_error() -> None:
    data = {
        "base_resp": {"status_code": 1004, "status_msg": "Account authentication failed"},
        "data": {},
    }
    b64, err, url = parse_minimax_image_payload(data)
    assert b64 is None
    assert err and "1004" in err
    assert url is None


def test_parse_minimax_sensitive_prompt() -> None:
    data = {
        "base_resp": {"status_code": 1026, "status_msg": "Sensitive content detected in prompt"},
        "data": {},
    }
    b64, err, url = parse_minimax_image_payload(data)
    assert b64 is None
    assert err and "1026" in err
    assert url is None


def test_parse_minimax_returns_first_url() -> None:
    data = {
        "base_resp": {"status_code": 0, "status_msg": "success"},
        "data": {"image_urls": ["https://example.com/a.png"]},
    }
    b64, err, url = parse_minimax_image_payload(data)
    assert b64 is None
    assert err is None
    assert url == "https://example.com/a.png"


def test_full_image_prompt_respects_minimax_cap() -> None:
    long_scene = "word " * 400
    p = _full_image_prompt(long_scene, max_total=MINIMAX_PROMPT_MAX)
    assert len(p) <= MINIMAX_PROMPT_MAX
    assert "Scene:" in p
    assert "paper" in p.lower() or "cutout" in p.lower()


def test_full_image_prompt_includes_style_keywords() -> None:
    p = _full_image_prompt("A developer stares at a whiteboard.", max_total=None)
    assert "Scene:" in p
    assert "south park" in p.lower()
    assert "cutout" in p.lower() or "construction" in p.lower() or "cardstock" in p.lower()
