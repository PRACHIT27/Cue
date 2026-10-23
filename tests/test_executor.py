import asyncio
from dataclasses import dataclass

import pytest

from cue.harness.events import RunEvents
from cue.harness.executor import execute
from cue.harness.plan import MAX_CALLS, Plan, PlanError, PlannedCall, Ref


@dataclass(frozen=True)
class FakeRef:
    id: str


class Clock:
    def __init__(self):
        self.starts = {}
        self.t0 = None

    def mark(self, name):
        now = asyncio.get_running_loop().time()
        self.t0 = self.t0 if self.t0 is not None else now
        self.starts[name] = now - self.t0


def tools_with(clock, delay=0.05):
    async def find(name):
        clock.mark("find")
        await asyncio.sleep(delay)
        return [FakeRef(f"id-{name}")]

    async def insights(kind, signal):
        clock.mark(kind)
        await asyncio.sleep(delay)
        return f"{kind} for {signal}"

    async def boom(**_):
        raise RuntimeError("Qloo said no")

    async def slow(**_):
        await asyncio.sleep(5)

    async def nothing(name):
        return []

    return {"find": find, "insights": insights, "boom": boom, "slow": slow, "nothing": nothing}


def run(plan, tools, timeout_s=1.0):
    events = []
    results = asyncio.run(execute(plan, tools, RunEvents("r_test", events.append), timeout_s=timeout_s))
    return results, events


KINDS = ["tv", "movies", "games", "podcasts", "brands"]


def artist_plan():
    calls = [PlannedCall("c1", "find", {"name": "Fake Artist"})]
    calls += [PlannedCall(f"c_{k}", "insights", {"kind": k, "signal": Ref("c1", "[0].id")}) for k in KINDS]
    return Plan(tuple(calls))


def test_dependent_calls_get_the_resolved_value():
    results, _ = run(artist_plan(), tools_with(Clock()))
    assert results["c_tv"].value == "tv for id-Fake Artist"
    assert all(r.status == "ok" for r in results.values())


def test_the_five_production_calls_start_together_after_the_search():
    clock = Clock()
    run(artist_plan(), tools_with(clock, delay=0.2))
    production_starts = [clock.starts[k] for k in KINDS]
    assert max(production_starts) - min(production_starts) < 0.05
    assert min(production_starts) >= 0.2


def test_a_timeout_marks_the_call_and_the_run_continues():
    plan = Plan((PlannedCall("c1", "slow"), PlannedCall("c2", "find", {"name": "Fake"})))
    results, _ = run(plan, tools_with(Clock()), timeout_s=0.1)
    assert results["c1"].status == "error" and "timed out" in results["c1"].error
    assert results["c2"].status == "ok"


def test_a_failure_skips_only_its_dependents():
    plan = Plan(
        (
            PlannedCall("c1", "boom"),
            PlannedCall("c2", "insights", {"kind": "tv", "signal": Ref("c1", "[0].id")}),
            PlannedCall("c3", "find", {"name": "Fake"}),
        )
    )
    results, _ = run(plan, tools_with(Clock()))
    assert results["c1"].status == "error" and "Qloo said no" in results["c1"].error
    assert results["c2"].status == "skipped" and "c1" in results["c2"].error
    assert results["c3"].status == "ok"


def test_an_empty_result_skips_dependents_instead_of_crashing():
    plan = Plan((PlannedCall("c1", "nothing", {"name": "Unknown"}), PlannedCall("c2", "insights", {"kind": "tv", "signal": Ref("c1", "[0].id")})))
    results, _ = run(plan, tools_with(Clock()))
    assert results["c1"].status == "ok"
    assert results["c2"].status == "skipped" and "nothing usable" in results["c2"].error


def test_refs_inside_lists_resolve_and_count_as_dependencies():
    call = PlannedCall("c2", "insights", {"kind": "tv", "signal": [Ref("c1", "[0].id")]})
    assert call.depends_on() == {"c1"}
    results, _ = run(Plan((PlannedCall("c1", "find", {"name": "X"}), call)), tools_with(Clock()))
    assert results["c2"].value == "tv for ['id-X']"


def test_events_have_run_id_sequence_and_one_start_and_end_per_call():
    results, events = run(artist_plan(), tools_with(Clock()))
    assert [e["seq"] for e in events] == list(range(1, len(events) + 1))
    assert all(e["run_id"] == "r_test" for e in events)
    for call_id in results:
        kinds = [e["kind"] for e in events if e.get("step") == call_id]
        assert kinds == ["step_start", "step_end"]


@pytest.mark.parametrize(
    "plan, message",
    [
        (Plan(tuple(PlannedCall(f"c{i}", "find", {"name": "x"}) for i in range(MAX_CALLS + 1))), "limit"),
        (Plan((PlannedCall("c1", "find"), PlannedCall("c1", "find"))), "share an id"),
        (Plan((PlannedCall("c1", "teleport"),)), "unknown tool"),
        (Plan((PlannedCall("c1", "insights", {"signal": Ref("c9")}),)), "unknown call"),
        (Plan((PlannedCall("c1", "insights", {"signal": Ref("c2")}), PlannedCall("c2", "insights", {"signal": Ref("c1")}))), "loop"),
    ],
)
def test_bad_plans_are_rejected_before_anything_runs(plan, message):
    with pytest.raises(PlanError, match=message):
        run(plan, tools_with(Clock()))


def test_ref_paths():
    data = {"items": [{"candidate": FakeRef("S-1")}]}
    assert Ref("c", "items[0].candidate.id").resolve(data) == "S-1"
    assert Ref("c").resolve("whole") == "whole"
