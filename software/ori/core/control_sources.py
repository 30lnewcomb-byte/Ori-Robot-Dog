"""Arbitration for Ori's concurrent control sources.

Auto-pilot, browser pilot, and voice are concurrent input sources, not
mutually-exclusive robot modes. Presence is tracked separately from control
intents so an open browser does not steal control from auto-pilot.
"""

from dataclasses import dataclass
from enum import IntEnum
from time import monotonic


class SourcePriority(IntEnum):
    AUTO = 10
    VOICE = 20
    BROWSER = 30
    SAFETY = 100


@dataclass
class ControlIntent:
    source: str
    kind: str
    payload: dict
    created_at: float
    ttl_s: float = 1.0

    @property
    def active(self) -> bool:
        return monotonic() - self.created_at <= self.ttl_s


class ControlArbiter:
    """Select the highest-priority active intent without changing robot modes."""

    def __init__(self) -> None:
        self._intents: dict[str, ControlIntent] = {}
        self._presence: dict[str, float] = {}
        self._safe = True

    def submit(self, source: str, kind: str, payload: dict | None = None, ttl_s: float = 1.0) -> ControlIntent:
        intent = ControlIntent(source, kind, payload or {}, monotonic(), ttl_s)
        self._intents[source] = intent
        if source == "safety" and kind == "safe":
            self._safe = True
        elif source != "safety":
            self._safe = False
        return intent

    def heartbeat(self, source: str, ttl_s: float = 1.5) -> None:
        self._presence[source] = monotonic() + ttl_s

    def presence(self) -> dict[str, bool]:
        now = monotonic()
        self._presence = {k: deadline for k, deadline in self._presence.items() if deadline > now}
        return {k: True for k in self._presence}

    def clear(self, source: str) -> None:
        self._intents.pop(source, None)

    def safe(self) -> None:
        self._safe = True
        self.submit("safety", "safe", {}, ttl_s=3600.0)

    def release_safe(self) -> None:
        self._safe = False
        self.clear("safety")

    def active(self) -> list[ControlIntent]:
        now = monotonic()
        self._intents = {k: v for k, v in self._intents.items() if now - v.created_at <= v.ttl_s}
        return list(self._intents.values())

    def select(self) -> ControlIntent | None:
        if self._safe:
            return self._intents.get("safety")
        intents = self.active()
        if not intents:
            return None
        return max(intents, key=lambda i: SourcePriority.__members__.get(i.source.upper(), SourcePriority.AUTO))
