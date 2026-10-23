from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

from cue.tools.records import EntityRef

FitStatus = Literal["ok", "insufficient_data"]


@dataclass(frozen=True)
class Match:
    source_id: str
    candidate: EntityRef
    affinity: float | None
    overlap: float | None = None
    audience: float | None = None
    trend: float | None = None
    trend_as_of: date | None = None
    explanation: dict[str, float] = field(default_factory=dict)

    @property
    def match_id(self) -> str:
        return f"{self.source_id}:{self.candidate.id}"


@dataclass(frozen=True)
class FitScore:
    match_id: str
    value: float | None
    status: FitStatus
    inputs: dict[str, Any] = field(default_factory=dict)
