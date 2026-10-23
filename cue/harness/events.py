from __future__ import annotations

import itertools
from typing import Any, Callable

from cue.qloo.events import QlooCallEvent

RunSink = Callable[[dict[str, Any]], None]


def ignore(event: dict[str, Any]) -> None:
    return None


class RunEvents:
    def __init__(self, run_id: str, sink: RunSink = ignore) -> None:
        self.run_id = run_id
        self._sink = sink
        self._seq = itertools.count(1)

    def emit(self, kind: str, **fields: Any) -> dict[str, Any]:
        event = {"run_id": self.run_id, "seq": next(self._seq), "kind": kind, **fields}
        self._sink(event)
        return event

    def qloo_sink(self, call: QlooCallEvent) -> None:
        fields = call.to_dict()
        fields.pop("kind", None)
        fields.pop("run_id", None)
        self.emit("qloo_call", **fields)
