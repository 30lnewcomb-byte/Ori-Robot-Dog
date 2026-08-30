# Ori Robotics Model

The **Ori Robotics Model** is Ori's custom local TensorFlow model. It is the primary learned-intelligence component; Gemini Robotics is a separate specialist service and is not the sole controller.

## Current implementation

`software/ori/core/ori_model.py` defines the first trainable model architecture:

- Python/TensorFlow implementation
- 64 normalized state/features as input
- 16 normalized joint-intent outputs
- bounded `tanh` output in `[-1, 1]`
- Huber training loss with Adam optimizer
- save/load through Keras
- no direct hardware or servo access

This is **model infrastructure, not a trained production model**. The repository does not yet claim a finished policy, dataset, or validated locomotion behavior.

## Control boundary

```text
Sensors / state
      |
      v
Ori Robotics Model (local TensorFlow)
      |
      v
Normalized joint intent
      |
      v
Local safety + limits + motion/control layer
      |
      v
Pi -> Pico controllers -> actuators
```

The model must never bypass the local safety/controller boundary. A model prediction is an intent, not permission to move a physical actuator.

## Training direction

Training data should eventually pair normalized robot state/perception features with validated target behavior. Simulation and recorded/approved trajectories should be used before physical deployment. Dataset schema, normalization constants, joint limits, and evaluation metrics must be versioned with the model.

## Gemini Robotics boundary

Gemini Robotics can be integrated as a higher-level robotics specialist through the Ori Platform when useful. It should augment the local Ori model rather than replace it. Cloud availability must not be required for the local safety layer or basic low-level control.
