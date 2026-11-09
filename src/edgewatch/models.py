"""Small, explicit data contracts: image-space observations only."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum


class Health(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    OBSERVING = "observing"
    DEGRADED = "degraded"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class Detection:
    label: str
    score: float
    x0: int
    y0: int
    x1: int
    y1: int

    def json(self) -> dict:
        return asdict(self)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")
