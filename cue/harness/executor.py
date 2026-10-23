from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Literal, Mapping

from cue.harness.events import RunEvents
from cue.harness.plan import Plan, PlannedCall, Ref

CALL_TIMEOUT_S = 10.0
CallStatus = Literal["ok", "error", "skipped"]
Tool = Callable[..., Awaitable[Any]]


@dataclass(frozen=True)
class CallResult:
    call_id: str
    tool: str
    status: CallStatus
    value: Any = None
    error: str | None = None
    ms: int = 0


class _Skip(Exception):
    pass


def _fill(value: Any, results: Mapping[str, CallResult]) -> Any:
    if isinstance(value, Ref):
        result = results[value.call_id]
        if result.status != "ok":
            raise _Skip(f"needs {value.call_id}, which did not succeed")
        try:
            return value.resolve(result.value)
        except (IndexError, KeyError, AttributeError, TypeError):
            raise _Skip(f"{value.call_id} returned nothing usable at {value.path or 'its result'}")
    if isinstance(value, dict):
        return {key: _fill(item, results) for key, item in value.items()}
    if isinstance(value, list):
        return [_fill(item, results) for item in value]
    if isinstance(value, tuple):
        return tuple(_fill(item, results) for item in value)
    return value


async def execute(
    plan: Plan,
    tools: Mapping[str, Tool],
    events: RunEvents,
    timeout_s: float = CALL_TIMEOUT_S,
) -> dict[str, CallResult]:
    plan.validate(set(tools))
    results: dict[str, CallResult] = {}
    tasks: dict[str, asyncio.Task] = {}

    async def run(call: PlannedCall) -> CallResult:
        deps = call.depends_on()
        if deps:
            await asyncio.gather(*(tasks[d] for d in deps))
        started = time.perf_counter()

        def finish(status: CallStatus, value: Any = None, error: str | None = None) -> CallResult:
            ms = round((time.perf_counter() - started) * 1000)
            result = CallResult(call.id, call.tool, status, value, error, ms)
            results[call.id] = result
            events.emit("step_end", step=call.id, tool=call.tool, status=status, ms=ms, error=error)
            return result

        try:
            args = _fill(call.args, results)
        except _Skip as reason:
            events.emit("step_start", step=call.id, tool=call.tool)
            return finish("skipped", error=str(reason))
        events.emit("step_start", step=call.id, tool=call.tool)
        try:
            value = await asyncio.wait_for(tools[call.tool](**args), timeout=timeout_s)
        except asyncio.TimeoutError:
            return finish("error", error=f"timed out after {timeout_s:g} s")
        except Exception as failure:
            return finish("error", error=f"{type(failure).__name__}: {failure}")
        return finish("ok", value=value)

    for call in plan.calls:
        tasks[call.id] = asyncio.create_task(run(call))
    await asyncio.gather(*tasks.values())
    return {call.id: results[call.id] for call in plan.calls}
