"""Local Ori Robotics model built with TensorFlow.

This module defines the trainable model architecture and its strict boundary
with robot control. It predicts a bounded 16-joint intent vector; it does not
send servo commands. The Pi-side safety/controller stack remains authoritative.

The model is intentionally small enough to target local inference on Ori's
Raspberry Pi, while keeping the feature/output schema explicit so training data
can evolve without silently changing the controller contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
import tensorflow as tf

INPUT_SIZE = 64
JOINT_COUNT = 16
OUTPUT_SIZE = JOINT_COUNT
MODEL_VERSION = "0.1.0"


@dataclass(frozen=True)
class ModelSpec:
    version: str = MODEL_VERSION
    input_size: int = INPUT_SIZE
    joint_count: int = JOINT_COUNT


class OriRoboticsModel:
    """Small local policy network for Ori's high-level robotics behavior.

    Inputs are normalized sensor/state features. Outputs are normalized joint
    intents in [-1, 1]. Conversion to physical joint limits belongs outside
    this model and must pass through the local safety layer.
    """

    def __init__(self, model: tf.keras.Model | None = None) -> None:
        self.spec = ModelSpec()
        self.model = model or self._build()

    @staticmethod
    def _build() -> tf.keras.Model:
        inputs = tf.keras.Input(shape=(INPUT_SIZE,), name="state_features")
        x = tf.keras.layers.Dense(128, activation="relu", name="dense_1")(inputs)
        x = tf.keras.layers.LayerNormalization(name="norm_1")(x)
        x = tf.keras.layers.Dense(96, activation="relu", name="dense_2")(x)
        x = tf.keras.layers.Dropout(0.10, name="dropout")(x)
        x = tf.keras.layers.Dense(64, activation="relu", name="dense_3")(x)
        outputs = tf.keras.layers.Dense(
            JOINT_COUNT, activation="tanh", name="joint_intent"
        )(x)
        return tf.keras.Model(inputs=inputs, outputs=outputs, name="ori_robotics_model")

    def compile(self, learning_rate: float = 1e-3) -> None:
        self.model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
            loss=tf.keras.losses.Huber(),
            metrics=[tf.keras.metrics.MeanAbsoluteError(name="mae")],
        )

    def predict(self, features: Sequence[float] | np.ndarray) -> np.ndarray:
        """Return one bounded 16-joint intent vector without commanding hardware."""
        values = np.asarray(features, dtype=np.float32)
        if values.shape != (INPUT_SIZE,):
            raise ValueError(f"expected {INPUT_SIZE} features, got shape {values.shape}")
        result = self.model(np.expand_dims(values, axis=0), training=False).numpy()[0]
        return np.clip(result, -1.0, 1.0)

    def train(
        self,
        features: np.ndarray,
        targets: np.ndarray,
        *,
        epochs: int = 1,
        batch_size: int = 32,
        validation_split: float = 0.2,
    ) -> tf.keras.callbacks.History:
        """Train from an explicit dataset; no hardware access occurs here."""
        x = np.asarray(features, dtype=np.float32)
        y = np.asarray(targets, dtype=np.float32)
        if x.ndim != 2 or x.shape[1] != INPUT_SIZE:
            raise ValueError(f"features must have shape (N, {INPUT_SIZE})")
        if y.ndim != 2 or y.shape[1] != JOINT_COUNT:
            raise ValueError(f"targets must have shape (N, {JOINT_COUNT})")
        if len(x) != len(y) or len(x) < 2:
            raise ValueError("features and targets must contain the same samples (at least 2)")
        if not 0.0 <= validation_split < 1.0:
            raise ValueError("validation_split must be in [0, 1)")
        self.compile()
        return self.model.fit(
            x,
            np.clip(y, -1.0, 1.0),
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            shuffle=True,
        )

    def save(self, path: str | Path) -> None:
        """Save the Keras model. Physical-control integration is not included."""
        self.model.save(path)

    @classmethod
    def load(cls, path: str | Path) -> "OriRoboticsModel":
        return cls(tf.keras.models.load_model(path))
