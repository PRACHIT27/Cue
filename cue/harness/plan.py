from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

MAX_CALLS = 40
_STEP = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)|\[(\d+)\]")


class PlanError(ValueError):
    pass


@dataclass(frozen=True)
class Ref:
    call_id: str
    path: str = ""

    def resolve(self, value: Any) -> Any:
        for name, index in _STEP.findall(self.path.replace(".", " ")):
            if index:
                value = value[int(index)]
            elif isinstance(value, dict):
                value = value[name]
            else:
                value = getattr(value, name)
        return value


@dataclass(frozen=True)
class PlannedCall:
    id: str
    tool: str
    args: dict[str, Any] = field(default_factory=dict)

    def depends_on(self) -> set[str]:
        found: set[str] = set()

        def walk(value: Any) -> None:
            if isinstance(value, Ref):
                found.add(value.call_id)
            elif isinstance(value, dict):
                for item in value.values():
                    walk(item)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    walk(item)

        walk(self.args)
        return found


@dataclass(frozen=True)
class Plan:
    calls: tuple[PlannedCall, ...]

    def validate(self, tools: set[str]) -> None:
        if len(self.calls) > MAX_CALLS:
            raise PlanError(f"plan has {len(self.calls)} calls; the limit is {MAX_CALLS}")
        ids = [call.id for call in self.calls]
        if len(set(ids)) != len(ids):
            raise PlanError("two calls share an id")
        known = set(ids)
        for call in self.calls:
            if call.tool not in tools:
                raise PlanError(f"{call.id} uses unknown tool {call.tool}")
            missing = call.depends_on() - known
            if missing:
                raise PlanError(f"{call.id} depends on unknown call {sorted(missing)[0]}")
        self._check_no_cycles()

    def _check_no_cycles(self) -> None:
        deps = {call.id: call.depends_on() for call in self.calls}
        done: set[str] = set()
        visiting: set[str] = set()

        def visit(node: str) -> None:
            if node in done:
                return
            if node in visiting:
                raise PlanError(f"calls depend on each other in a loop at {node}")
            visiting.add(node)
            for dep in deps[node]:
                visit(dep)
            visiting.discard(node)
            done.add(node)

        for node in deps:
            visit(node)
