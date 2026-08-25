"""Small deterministic voice-command adapter.

Speech recognition is intentionally separate from robot control. A future
voice/AI layer can replace this parser without changing the control API.
"""


def parse_voice(text: str) -> tuple[str, dict] | None:
    t = " ".join(text.lower().strip().split())
    if not t:
        return None
    if t in {"stop", "halt", "freeze"}:
        return "drive", {"direction": "stop", "speed": 0}
    if "stand" in t:
        return "stand", {}
    if "sit" in t:
        return "sit", {}
    if "auto pilot on" in t or "autopilot on" in t or "start auto pilot" in t:
        return "auto_start", {}
    if "auto pilot off" in t or "autopilot off" in t or "stop auto pilot" in t:
        return "auto_stop", {}
    for words, direction in [
        (("forward", "ahead"), "forward"),
        (("backward", "back", "reverse"), "backward"),
        (("left",), "left"),
        (("right",), "right"),
    ]:
        if any(word in t for word in words):
            return "drive", {"direction": direction, "speed": 0.35}
    return None
