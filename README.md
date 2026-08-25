# Ori Robot Dog

Software architecture for the Ori quadruped robot.

## Hardware baseline

- Raspberry Pi 3 — main computer
- 2–3 Raspberry Pi Pico boards — distributed real-time control and I/O
- 16 × HTD-45H servos in the current CAD baseline
- 3S LiPo is the current battery-class candidate; final pack is not selected yet

## Software goals

Ori is designed around a layered architecture:

```text
Raspberry Pi 3
     │
     ├── high-level behavior
     ├── perception
     ├── kinematics
     ├── coordination
     └── communications
              │
        ┌─────┴─────┐
        │            │
      Pico(s)   hardware I/O
        │
      servos / sensors
```

The Pi should not be responsible for hard real-time servo timing. Pico firmware will own low-level hardware control and safety behavior.

## Development rule

Build the software architecture before committing to physical wiring. Hardware-specific values should live in configuration, not be scattered through control code.

## Status

Early software foundation. No physical robot is required to run the initial software tests.
