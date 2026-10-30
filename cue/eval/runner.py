from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from cue.eval.scorers import RowScore, failed_row, row_dict, score_row, summarise
from cue.eval.systems import EvalRecord, ResolveFn, SystemFn


def load_records(path: Path, split: str = "all") -> list[EvalRecord]:
    records: list[EvalRecord] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = EvalRecord.from_json(json.loads(line))
        except (json.JSONDecodeError, KeyError, ValueError) as problem:
            raise ValueError(f"{path}:{number}: {problem}") from problem
        if split == "all" or record.split == split:
            records.append(record)
    ids = [r.id for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: duplicate ids")
    return records


async def evaluate(
    records: Iterable[EvalRecord],
    systems: Mapping[str, SystemFn],
    resolve: ResolveFn,
    spent: Callable[[], float],
    cap: float,
    on_row: Callable[[RowScore], None] = lambda _row: None,
) -> tuple[list[RowScore], dict[str, dict[str, list[str]]]]:
    rows: list[RowScore] = []
    details: dict[str, dict[str, list[str]]] = {}
    for record in records:
        for name, system in systems.items():
            started, before = time.perf_counter(), spent()
            try:
                suggestions = await system(record)
            except Exception as problem:
                row = failed_row(record.id, name, record.mode, f"{type(problem).__name__}: {problem}"[:200],
                                 time.perf_counter() - started, spent() - before)
            else:
                elapsed, usd = time.perf_counter() - started, spent() - before
                resolved = [await resolve(s, record.mode) for s in suggestions]
                row = score_row(record.id, name, record.mode, record.answer, suggestions, resolved, cap, elapsed, usd)
                details.setdefault(record.id, {})[name] = suggestions
            rows.append(row)
            on_row(row)
    return rows, details


def results_document(rows: list[RowScore], split: str, cap: float, prompt_version: str) -> dict[str, Any]:
    return {
        "generated": time.strftime("%Y-%m-%d %H:%M"),
        "split": split,
        "systems": {"llm": "Claude alone, no tools", "cue": "Cue: Qloo data, code scoring, grounding guard"},
        "popularity_cap": cap,
        "prompt_version": prompt_version,
        "summary": summarise(rows),
        "rows": [row_dict(r) for r in rows],
    }
