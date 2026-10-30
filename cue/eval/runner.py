from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from cue.eval.scorers import RowScore, failed_row, repeat_share, row_dict, score_row, summarise
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
        answer_popularity = None
        if record.mode == "supervisor" and record.answer:
            answer_popularity = (await resolve(record.answer, record.mode)).popularity
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
                row = score_row(record.id, name, record.mode, record.answer, suggestions, resolved, cap, elapsed, usd, answer_popularity)
                details.setdefault(record.id, {})[name] = suggestions
            rows.append(row)
            on_row(row)
    return rows, details


def results_document(
    rows: list[RowScore],
    split: str,
    cap: float,
    prompt_version: str,
    details: Mapping[str, Mapping[str, list[str]]] | None = None,
) -> dict[str, Any]:
    summary = summarise(rows)
    for system in summary:
        summary[system]["repeat_share"] = repeat_share([d[system] for d in (details or {}).values() if system in d])
    return {
        "generated": time.strftime("%Y-%m-%d %H:%M"),
        "split": split,
        "systems": {"llm": "Claude alone, no tools", "cue": "Cue: Qloo data, code scoring, grounding guard"},
        "popularity_cap": cap,
        "prompt_version": prompt_version,
        "definitions": {
            "hit_rate_top10": "Share of rows where the known answer is in the system's top 10, by name.",
            "made_up_rate": "Share of suggested names Qloo has no exact match for. Not found in Qloo, which is not always invented.",
            "under_the_radar_share": "Supervisor rows: share of found artists at or under the popularity cap.",
            "answers_above_cap": "Supervisor rows whose known answer is above the popularity cap. Cue leaves such artists out by design, so these rows are not scored for hits, for any system.",
            "repeat_share": "Share of suggestions that the same system also gave to at least two other inputs. High means generic answers.",
            "median_suggestion_popularity": "How popular the suggested productions or artists are in Qloo (0 to 1). Lower means smaller, more reachable placements.",
        },
        "caveats": [
            "Known placements are famous, so Claude alone may recall them from training rather than reason about taste.",
            "Qloo's taste data can reflect a placement after it happened, which may help Cue on old placements.",
            "Two systems only: Claude alone and Cue. Claude with web search was not run.",
        ],
        "summary": summary,
        "rows": [row_dict(r) for r in rows],
    }
