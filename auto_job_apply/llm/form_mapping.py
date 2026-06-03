from __future__ import annotations


def low_confidence(confidence: float, threshold: float = 0.75) -> bool:
    return confidence < threshold
