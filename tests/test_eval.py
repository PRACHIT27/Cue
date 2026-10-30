import asyncio
import json

import pytest

from cue.eval.runner import evaluate, load_records, results_document
from cue.eval.scorers import Resolved, is_hit, normalise, score_row, summarise
from cue.eval.systems import EvalRecord


def test_normalise_ignores_case_accents_punctuation_and_leading_the():
    assert normalise("The Bear") == normalise("bear")
    assert normalise("Beyoncé") == normalise("beyonce")
    assert normalise("Dex & the Kites") == normalise("Dex and the Kites")


def test_hit_only_counts_the_top_ten():
    names = [f"Show {i}" for i in range(12)]
    assert is_hit("show 3", names) is True
    assert is_hit("Show 11", names) is False
    assert is_hit(None, names) is None


def test_score_row_counts_made_up_and_emerging():
    resolved = [Resolved("A", True, 0.4), Resolved("B", True, 0.95), Resolved("C", False, None)]
    row = score_row("p1", "llm", "supervisor", "A", ["A", "B", "C"], resolved, 0.8, 1.234, 0.01)
    assert (row.hit, row.suggested, row.made_up, row.resolved, row.emerging) == (True, 3, 1, 2, 1)
    artist_row = score_row("p2", "cue", "artist", "X", ["A"], [Resolved("A", True, 0.99)], 0.8, 1, 0)
    assert artist_row.emerging == 0


def test_summary_rates():
    rows = [
        score_row("p1", "cue", "artist", "A", ["A"], [Resolved("A", True, 0.5)], 0.8, 2, 0.01),
        score_row("p2", "cue", "artist", "Z", ["A", "B"], [Resolved("A", True, 0.5), Resolved("B", False, None)], 0.8, 4, 0.02),
    ]
    s = summarise(rows)["cue"]
    assert s["hit_rate_top10"] == 0.5
    assert s["made_up_rate"] == round(1 / 3, 4)
    assert s["median_seconds"] == 3
    assert s["emerging_share"] is None


def test_load_records_filters_split_and_rejects_duplicates(tmp_path):
    path = tmp_path / "set.jsonl"
    rows = [
        {"id": "p1", "split": "dev", "mode": "artist", "input": "Fake Artist", "answer": "Fake Show", "source": "https://example.com"},
        {"id": "p2", "split": "test", "mode": "supervisor", "input": "Fake Show", "answer": None, "source": "", "type": "movie"},
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    assert [r.id for r in load_records(path, "dev")] == ["p1"]
    assert load_records(path, "test")[0].type == "movie"
    path.write_text("\n".join(json.dumps(r) for r in rows + rows[:1]), encoding="utf-8")
    with pytest.raises(ValueError):
        load_records(path)


def test_evaluate_scores_each_system_and_survives_a_failure():
    records = [EvalRecord("p1", "dev", "artist", "Fake Artist", "Real Show", "src")]

    async def good(record):
        return ["Real Show", "Invented Show"]

    async def broken(record):
        raise RuntimeError("boom")

    async def resolve(name, mode):
        return Resolved(name, name == "Real Show", 0.5 if name == "Real Show" else None)

    spent = iter([0.0, 0.01, 0.01, 0.01]).__next__
    rows, details = asyncio.run(evaluate(records, {"llm": good, "cue": broken}, resolve, spent, 0.8))
    by = {r.system: r for r in rows}
    assert by["llm"].hit is True and by["llm"].made_up == 1 and by["llm"].usd == 0.01
    assert by["cue"].error.startswith("RuntimeError")
    assert details == {"p1": {"llm": ["Real Show", "Invented Show"]}}
    doc = results_document(rows, "dev", 0.8, "v")
    assert doc["summary"]["cue"]["errors"] == 1
    assert "Invented Show" not in json.dumps(doc)


def test_the_shipped_eval_set_is_well_formed():
    from pathlib import Path

    records = load_records(Path("evalsets/placements.jsonl"))
    assert len(records) >= 40
    assert all(r.mode in ("artist", "supervisor") for r in records)
    assert all(r.answer for r in records if r.mode == "artist")
    assert all(r.source.startswith("https://") for r in records if r.answer)
    assert {r.split for r in records} == {"dev", "test"}
    assert all(r.type in ("tv_show", "movie", "videogame", "podcast", "brand") for r in records if r.mode == "supervisor")


def test_supervisor_hit_counts_with_an_emerging_answer():
    resolved = [Resolved("Baby Queen", True, 0.42), Resolved("Famous Star", True, 0.97)]
    row = score_row("s03", "cue", "supervisor", "Baby Queen", ["Famous Star", "Baby Queen"], resolved, 0.8, 1, 0)
    assert (row.hit, row.emerging, row.made_up) == (True, 1, 0)
