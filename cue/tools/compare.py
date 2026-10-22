from __future__ import annotations

from typing import Any, Mapping

from cue.qloo.params import COMPARE
from cue.tools.context import qloo_get
from cue.tools.parse import tag_ref
from cue.tools.records import CompareResult, TagRef

TAKE = 50


def _side_tags(side: Any) -> tuple[TagRef, ...]:
    raw_tags = side.get("tags") if isinstance(side, Mapping) else side
    refs = []
    for raw in raw_tags or []:
        try:
            refs.append(tag_ref(raw))
        except (ValueError, AttributeError):
            continue
    return tuple(refs)


async def compare(a_ids: list[str], b_ids: list[str]) -> CompareResult:
    data = await qloo_get(
        COMPARE,
        {"a.signal.interests.entities": a_ids, "b.signal.interests.entities": b_ids, "take": TAKE},
    )
    results = data.get("results") if isinstance(data, Mapping) else None
    results = results if isinstance(results, Mapping) else {}
    shared = []
    for raw in results.get("tags") or []:
        try:
            score = float((raw.get("query") or {}).get("score", 0.0))
            shared.append((tag_ref(raw), max(0.0, min(1.0, score))))
        except (ValueError, TypeError, AttributeError):
            continue
    return CompareResult(
        a_ids=tuple(a_ids),
        b_ids=tuple(b_ids),
        shared=tuple(shared),
        a_tags=_side_tags(results.get("a")),
        b_tags=_side_tags(results.get("b")),
    )
