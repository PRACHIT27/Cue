from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable, Literal

CacheState = Literal["hit", "miss", "skipped"]
CallStatus = Literal["ok", "error", "rejected"]


@dataclass(frozen=True)
class QlooCallEvent:
    endpoint: str
    params: dict[str, str]
    ms: int
    cache: CacheState
    status: CallStatus
    run_id: str | None = None
    result_count: int | None = None
    http_status: int | None = None
    attempts: int = 0
    error: str | None = None
    kind: str = "qloo_call"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


EventSink = Callable[[QlooCallEvent], None]


def discard(event: QlooCallEvent) -> None:
    return None


def result_count(data: Any) -> int | None:
    if not isinstance(data, dict):
        return None
    results = data.get("results")
    if isinstance(results, list):
        return len(results)
    if isinstance(results, dict):
        for value in results.values():
            if isinstance(value, list):
                return len(value)
    return None
