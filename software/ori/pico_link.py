"""Pi-side newline-JSON transport to Pico controllers.

USB serial is used as the initial transport abstraction. The exact Pico USB
ports/paths and physical wiring are configuration, not hard-coded here.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass

try:
    import serial
except ImportError:  # keeps the module importable in tests without hardware
    serial = None


@dataclass
class PicoLink:
    controller_id: str
    port: str
    baudrate: int = 115200

    def __post_init__(self) -> None:
        self._serial = None
        self._lock = threading.Lock()

    def connect(self) -> None:
        if serial is None:
            raise RuntimeError("pyserial is required on the Raspberry Pi")
        self._serial = serial.Serial(self.port, self.baudrate, timeout=0.05)

    def close(self) -> None:
        if self._serial:
            self._serial.close()
            self._serial = None

    @property
    def connected(self) -> bool:
        return bool(self._serial and self._serial.is_open)

    def send(self, message: dict) -> None:
        if not self.connected:
            raise RuntimeError(f"{self.controller_id} is not connected")
        payload = (json.dumps(message, separators=(",", ":")) + "\n").encode()
        with self._lock:
            self._serial.write(payload)

    def safe(self) -> None:
        self.send({"type": "safe"})

    def release_safety(self) -> None:
        self.send({"type": "release_safety"})

    def set_joint(self, joint: str, position_deg: float, velocity_deg_s: float | None = None, sequence: int = 0) -> None:
        message = {"type": "joint_set", "joint": joint, "position_deg": position_deg, "sequence": sequence}
        if velocity_deg_s is not None:
            message["velocity_deg_s"] = velocity_deg_s
        self.send(message)
