from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Literal

from cue.agents.artist_run import run_artist
from cue.agents.supervisor_run import SHORTLIST_LABEL, run_supervisor
from cue.api.serialize import jsonable
from cue.harness.events import RunEvents
from cue.qloo.cache import Cache
from cue.qloo.client import QlooClient
from cue.qloo.ratelimit import TokenBucket
from cue.qloo.settings import QlooSettings
from cue.tools import use_client

RunStatus = Literal["running", "done", "error"]
Mode = Literal["artist", "supervisor"]
KEEP_S = 2 * 60 * 60
SECTIONS = ("big_screen", "prime_time", "indie_gems")


@dataclass
class RunState:
    run_id: str
    mode: Mode
    request: dict[str, Any]
    status: RunStatus = "running"
    events: list[dict[str, Any]] = field(default_factory=list)
    result: dict[str, Any] | None = None
    error: str | None = None
    started: float = field(default_factory=time.time)
    finished: float | None = None

    def summary(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "mode": self.mode,
            "status": self.status,
            "request": self.request,
            "result": self.result,
            "error": self.error,
            "seconds": round((self.finished or time.time()) - self.started, 1),
            "qloo_calls": sum(1 for e in self.events if e["kind"] == "qloo_call"),
            "endpoints": sorted({e["endpoint"] for e in self.events if e["kind"] == "qloo_call"}),
        }


ALSO_PER_TYPE = 4


def also_love(run: Any, per_type: int = ALSO_PER_TYPE) -> dict[str, list[dict[str, Any]]]:
    pitched = {item.candidate.id for item in run.kit.items}
    scores = {s.match_id: s for s in run.scores if s.status == "ok" and s.value is not None}
    by_type: dict[str, list[dict[str, Any]]] = {}
    for match in run.matches:
        fit = scores.get(match.match_id)
        if fit is None or match.candidate.id in pitched:
            continue
        by_type.setdefault(match.candidate.type, []).append(
            {
                "id": match.candidate.id,
                "name": match.candidate.name,
                "type": match.candidate.type,
                "popularity": match.candidate.popularity,
                "fit": fit.value,
                "lift": fit.inputs.get("lift"),
                "audience": fit.inputs.get("audience"),
                "section": fit.inputs.get("section"),
            }
        )
    return {kind: sorted(rows, key=lambda r: -r["fit"])[:per_type] for kind, rows in by_type.items()}


def artist_result(run: Any) -> dict[str, Any]:
    items = [jsonable(item) for item in run.kit.items]
    return {
        "pitches": items,
        "sections": {s: [i for i in items if i["fit"]["inputs"].get("section") == s] for s in SECTIONS},
        "also_love": also_love(run),
        "matches_scored": len(run.matches),
        "dropped": [jsonable(d) for d in run.drops],
        "decisions": [jsonable(d) for d in run.decisions],
    }


def supervisor_result(run: Any) -> dict[str, Any]:
    return {
        "label": SHORTLIST_LABEL,
        "cap": run.cap,
        "artists": [jsonable(item) for item in run.brief.artists],
        "matches_scored": len(run.matches),
        "dropped": [jsonable(d) for d in run.drops],
    }


class RunManager:
    def __init__(
        self,
        settings: QlooSettings,
        cache: Cache,
        limiter: TokenBucket,
        max_concurrent: int = 3,
        artist: Callable[..., Awaitable[Any]] = run_artist,
        supervisor: Callable[..., Awaitable[Any]] = run_supervisor,
        transport: Any = None,
    ) -> None:
        self.settings = settings
        self.cache = cache
        self.limiter = limiter
        self.runs: dict[str, RunState] = {}
        self._slots = asyncio.Semaphore(max_concurrent)
        self._artist = artist
        self._supervisor = supervisor
        self._transport = transport
        self._tasks: set[asyncio.Task] = set()

    def client(self, sink: Any = None) -> QlooClient:
        kwargs = {"cache": self.cache, "limiter": self.limiter, "transport": self._transport}
        if sink is not None:
            kwargs["sink"] = sink
        return QlooClient(self.settings, **kwargs)

    def prune(self) -> None:
        cutoff = time.time() - KEEP_S
        for run_id in [r for r, s in self.runs.items() if s.finished and s.finished < cutoff]:
            del self.runs[run_id]

    def start(self, mode: Mode, request: dict[str, Any]) -> RunState:
        self.prune()
        state = RunState(f"r_{uuid.uuid4().hex[:12]}", mode, request)
        self.runs[state.run_id] = state
        task = asyncio.create_task(self._run(state))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return state

    async def _run(self, state: RunState) -> None:
        events = RunEvents(state.run_id, state.events.append)
        request = state.request
        status: RunStatus = "error"
        if request.get("route"):
            events.emit("onboarding", route=request["route"])
        try:
            async with self._slots:
                async with self.client(sink=events.qloo_sink) as client:
                    with use_client(client, run_id=state.run_id):
                        if state.mode == "artist":
                            run = await self._artist(
                                list(request["signal_ids"]),
                                request["artist_name"],
                                events,
                                brief=request.get("brief", ""),
                                basis=request.get("basis", "measured"),
                            )
                            state.result = artist_result(run)
                        else:
                            run = await self._supervisor(
                                request["production_id"],
                                request["production_name"],
                                request["production_type"],
                                events,
                                brief=request.get("brief", ""),
                            )
                            state.result = supervisor_result(run)
            status = "done"
        except Exception as failure:
            state.error = f"{type(failure).__name__}: {failure}"
            events.emit("error", error=state.error)
        finally:
            events.emit("run_end", status=status)
            state.finished = time.time()
            state.status = status

    async def stream(self, run_id: str, poll_s: float = 0.25):
        state = self.runs[run_id]
        sent = 0
        while True:
            while sent < len(state.events):
                yield state.events[sent]
                sent += 1
            if state.status != "running" and sent >= len(state.events):
                return
            await asyncio.sleep(poll_s)
