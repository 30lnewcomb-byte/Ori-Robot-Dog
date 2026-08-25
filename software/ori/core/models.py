"""Core data models shared by Ori's high-level software."""

from dataclasses import dataclass, field
from enum import Enum
from time import monotonic
from typing import Mapping


class ControllerState(str, Enum):
    UNKNOWN = "unknown"
    READY = "ready"
    ACTIVE = "active"
    FAULT = "fault"
    SAFE = "safe"


@dataclass(frozen=True)
class JointCommand:
    """A high-level joint command; units are radians and rad/s."""

    joint_id: str
    position_rad: float
    velocity_rad_s: float | None = None
    sequence: int = 0


@dataclass(frozen=True)
class JointTelemetry:
    joint_id: str
    position_rad: float
    velocity_rad_s: float = 0.0
    temperature_c: float | None = None
    voltage_v: float | None = None
    fault: str | None = None


@dataclass
class ControllerTelemetry:
    controller_id: str
    state: ControllerState = ControllerState.UNKNOWN
    joints: dict[str, JointTelemetry] = field(default_factory=dict)
    timestamp: float = field(default_factory=monotonic)

    @classmethod
    def from_mapping(cls, controller_id: str, data: Mapping[str, JointTelemetry]) -> "ControllerTelemetry":
        return cls(controller_id=controller_id, joints=dict(data))
