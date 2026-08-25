# Ori Robot Dog

Software architecture and control stack for the Ori quadruped robot.

## Hardware baseline

- Raspberry Pi 3 — main computer / API / coordination
- 2–3 Raspberry Pi Pico boards — distributed real-time control and I/O
- 16 × HTD-45H servos in the current CAD baseline
- 3S LiPo is the current battery-class candidate; final pack is not selected yet

## Control philosophy

Ori does **not** treat browser control, voice, and auto-pilot as mutually-exclusive robot modes.

They are input sources:

```text
                  ORI CONTROL
                       │
       ┌───────────────┼───────────────┐
       │               │               │
   AUTO-PILOT       BROWSER          VOICE
       │               │               │
       └───────────────┼───────────────┘
                       ▼
                Pi control arbiter
                       │
                 selected intent
                       ▼
                Pico controllers
                       │
                    servos
```

Auto-pilot can remain running in the background. Opening the browser does not automatically take control. A live browser input temporarily gets higher priority, while voice can issue commands independently. Safety is a separate highest-priority state.

## Browser pilot

The `web/` application is designed like a camera-drone controller:

- live camera viewport
- browser movement controls
- telemetry
- auto-pilot controls
- voice input
- Pi API connection

The browser sends high-level intents. It never owns real-time servo timing.

## Raspberry Pi software

`software/ori/pi_server.py` provides the Pi API:

- REST command API
- WebSocket telemetry
- source presence heartbeats
- voice intent endpoint
- explicit safety release
- camera signaling boundary
- auto-pilot state boundary

`software/ori/pico_link.py` provides the Pi → Pico serial transport.

## Pico firmware

`firmware/pico/controller.py` provides:

- packet parsing
- local safe state
- command watchdog
- telemetry
- actuator adapter boundary

The exact HTD-45H electrical/serial driver is intentionally not guessed until the final servo bus and wiring are selected.

## Important safety rule

A stale browser, voice command, or network connection must not be able to keep Ori moving indefinitely. Safety is handled separately from ordinary input sources, and Pico watchdogs provide another layer below the Pi.

No physical robot is required to run the initial software tests.
