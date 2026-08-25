"""Ori Pico controller firmware skeleton (MicroPython).

This is the real-time safety/protocol layer. It deliberately does not guess the
HTD-45H's electrical/serial packet format. The ServoBus adapter is the only
hardware-specific piece that must be bound once the exact servo bus wiring is
selected.

Protocol: newline-delimited JSON over USB/UART between Pi and Pico.
"""

import json
import time

WATCHDOG_MS = 500
TELEMETRY_MS = 100


class ServoBus:
    """Hardware adapter boundary for the selected serial servo bus."""

    def set_position(self, joint_id, position_deg, velocity_deg_s=None):
        raise NotImplementedError("Bind the verified HTD-45H bus driver here")

    def stop_all(self):
        pass

    def read_telemetry(self):
        return {}


class MockServoBus(ServoBus):
    """Safe bench/simulation adapter; never drives physical servos."""

    def __init__(self):
        self.positions = {}

    def set_position(self, joint_id, position_deg, velocity_deg_s=None):
        self.positions[str(joint_id)] = float(position_deg)

    def stop_all(self):
        pass

    def read_telemetry(self):
        return {k: {"position_deg": v} for k, v in self.positions.items()}


class PicoController:
    def __init__(self, controller_id, servo_bus):
        self.controller_id = controller_id
        self.bus = servo_bus
        self.safe = True
        self.last_command_ms = time.ticks_ms()
        self.sequence = 0

    def touch_watchdog(self):
        self.last_command_ms = time.ticks_ms()

    def watchdog_expired(self):
        return time.ticks_diff(time.ticks_ms(), self.last_command_ms) > WATCHDOG_MS

    def enter_safe(self, reason):
        self.safe = True
        self.bus.stop_all()
        self.emit({"type": "fault", "controller": self.controller_id, "fault": reason})

    def handle(self, message):
        msg_type = message.get("type")
        if msg_type == "ping":
            self.touch_watchdog()
            self.emit({"type": "pong", "controller": self.controller_id})
            return

        if msg_type == "safe":
            self.enter_safe("remote_safe")
            return

        if msg_type == "release_safety":
            self.safe = False
            self.touch_watchdog()
            self.emit({"type": "ready", "controller": self.controller_id})
            return

        if msg_type == "joint_set":
            if self.safe:
                self.emit({"type": "rejected", "reason": "safe"})
                return
            joint = message.get("joint")
            position = message.get("position_deg")
            if joint is None or position is None:
                self.emit({"type": "rejected", "reason": "invalid_joint_set"})
                return
            self.bus.set_position(joint, position, message.get("velocity_deg_s"))
            self.sequence = int(message.get("sequence", self.sequence + 1))
            self.touch_watchdog()
            return

        self.emit({"type": "rejected", "reason": "unknown_message"})

    def telemetry(self):
        return {
            "type": "telemetry",
            "controller": self.controller_id,
            "safe": self.safe,
            "sequence": self.sequence,
            "joints": self.bus.read_telemetry(),
        }

    def emit(self, message):
        print(json.dumps(message))


def run(controller_id="pico-1", bus=None):
    controller = PicoController(controller_id, bus or MockServoBus())
    last_telemetry = time.ticks_ms()
    while True:
        if controller.watchdog_expired() and not controller.safe:
            controller.enter_safe("command_timeout")

        # MicroPython USB/stdin availability differs by firmware build. This
        # loop keeps protocol parsing isolated so the transport can be swapped.
        try:
            line = input()
            if line:
                controller.handle(json.loads(line))
        except (EOFError, ValueError):
            pass

        now = time.ticks_ms()
        if time.ticks_diff(now, last_telemetry) >= TELEMETRY_MS:
            controller.emit(controller.telemetry())
            last_telemetry = now
        time.sleep_ms(5)


if __name__ == "__main__":
    run()
