"""Safe local learning utilities for the Ori Robotics Model.

Learning is deliberately offline/reviewable: experiences are recorded as data,
then training updates the model from an explicit dataset. This prevents a live
robot from silently changing its policy while it is moving.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

from .ori_model import INPUT_SIZE, JOINT_COUNT, OriRoboticsModel


@dataclass(frozen=True)
class Experience:
    """One approved state -> target-behavior training example."""

    features: tuple[float, ...]
    target: tuple[float, ...]

    def validate(self) -> None:
        if len(self.features) != INPUT_SIZE:
            raise ValueError(f"expected {INPUT_SIZE} features")
        if len(self.target) != JOINT_COUNT:
            raise ValueError(f"expected {JOINT_COUNT} joint targets")
        if not np.all(np.isfinite(self.features)) or not np.all(np.isfinite(self.target)):
            raise ValueError("experience contains non-finite values")
        if np.any(np.asarray(self.target) < -1.0) or np.any(np.asarray(self.target) > 1.0):
            raise ValueError("targets must be normalized to [-1, 1]")


def experiences_to_arrays(experiences: Iterable[Experience]) -> tuple[np.ndarray, np.ndarray]:
    items = list(experiences)
    if not items:
        raise ValueError("at least one experience is required")
    for item in items:
        item.validate()
    return (
        np.asarray([item.features for item in items], dtype=np.float32),
        np.asarray([item.target for item in items], dtype=np.float32),
    )


def train_from_experiences(
    model: OriRoboticsModel,
    experiences: Iterable[Experience],
    *,
    epochs: int = 5,
    batch_size: int = 32,
    validation_split: float = 0.2,
):
    """Train the local model from approved data and return Keras History.

    This function intentionally has no hardware imports or actuator calls.
    Deploy a trained model only after evaluation and human review.
    """
    features, targets = experiences_to_arrays(experiences)
    return model.train(
        features,
        targets,
        epochs=epochs,
        batch_size=batch_size,
        validation_split=validation_split,
    )


def save_training_arrays(
    experiences: Iterable[Experience], path: str | Path
) -> None:
    """Persist an approved dataset in a simple NumPy archive."""
    features, targets = experiences_to_arrays(experiences)
    np.savez_compressed(path, features=features, targets=targets)
