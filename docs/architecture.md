# Ori Software Architecture

## 1. System layers

### Raspberry Pi 3

The Pi is Ori's high-level computer. It owns:

- behavior and task coordination
- perception
- kinematics and motion planning
- system state
- telemetry aggregation
- communication with Pico controllers

The Pi should issue **intent-level or motion-level commands**, not depend on Linux timing for individual servo pulses.

### Raspberry Pi Pico controllers

Two or three Picos will provide distributed low-level control. The exact board assignment remains a planning decision until the final sensor and actuator inventory is complete.

A Pico is responsible for:

- deterministic actuator control
- reading directly attached sensors
- local limits and sanity checks
- watchdog behavior
- reporting telemetry to the Pi

## 2. Proposed communication model

```text
Pi
 │
 │ command / configuration
 ▼
Pico controller
 │
 ├── actuator outputs
 ├── local sensors
 └── safety state
 │
 │ telemetry / faults
 ▼
Pi
```

The protocol should be packet-based and versioned. It should support:

- device identification
- sequence numbers
- timestamps
- command type
- payload
- acknowledgement/status
- fault reporting

## 3. Safety principle

Loss of communication with the Pi must **not** cause a Pico to blindly continue an unlimited motion command. Controllers need command timeouts and a defined safe state.

Software safety is not a substitute for a physical emergency-stop/power-disconnect design.

## 4. Configuration principle

Hardware constants belong in configuration:

- joint IDs
- servo limits
- calibration offsets
- sensor assignments
- controller IDs
- communication settings

Application logic should not contain scattered magic numbers.

## 5. Development stages

1. Define protocol and message schemas.
2. Build Pi-side communication library.
3. Build Pico-side protocol parser and simulator.
4. Add simulated joints/sensors.
5. Add hardware drivers.
6. Add kinematics and coordinated motion.
7. Integrate physical hardware only after software simulation/tests are passing.
