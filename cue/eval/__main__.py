from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

from cue.agents.common.llm import Budget
from cue.eval.runner import evaluate, load_records, results_document
from cue.eval.scorers import RowScore
from cue.eval.systems import CAP, EVAL_PROMPT_VERSION, SYSTEMS, qloo_resolve
from cue.qloo.client import QlooClient
from cue.qloo.settings import QlooSettings
from cue.qloo.smoke import _load_dotenv
from cue.tools import use_client

DETAILS_DIR = Path(".cache/eval")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m cue.eval", description="Compare Claude alone with Cue on known placements.")
    p.add_argument("--set", dest="set_path", default="evalsets/placements.jsonl")
    p.add_argument("--split", default="all", choices=["dev", "test", "all"])
    p.add_argument("--systems", default="llm,cue", help="comma-separated: llm, cue")
    p.add_argument("--limit", type=int, default=0, help="only the first N rows")
    p.add_argument("--out", default="eval/results.json")
    return p


def _print_row(row: RowScore) -> None:
    hit = "-" if row.hit is None else ("HIT" if row.hit else "miss")
    status = row.error or f"{hit:<4} made-up {row.made_up}/{row.made_up + row.resolved}"
    print(f"  {row.id:<8} {row.system:<4} {row.seconds:>6.1f}s  {status}")


async def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    chosen = [s.strip() for s in args.systems.split(",") if s.strip()]
    unknown = [s for s in chosen if s not in SYSTEMS]
    if unknown:
        print(f"Unknown systems: {', '.join(unknown)}. Choose from {', '.join(SYSTEMS)}.")
        return 2
    records = load_records(Path(args.set_path), args.split)
    if args.limit:
        records = records[: args.limit]
    if not records:
        print(f"No rows in {args.set_path} for split {args.split!r}.")
        return 1
    print(f"Evaluating {len(records)} rows · systems {', '.join(chosen)} · split {args.split}")
    budget = Budget.from_env()
    run_id = f"eval_{int(time.time())}"
    async with QlooClient(QlooSettings.from_env({**_load_dotenv(), **os.environ})) as client:
        with use_client(client, run_id=run_id):
            rows, details = await evaluate(records, {s: SYSTEMS[s] for s in chosen}, qloo_resolve, budget.spent, CAP, _print_row)
    document = results_document(rows, args.split, CAP, EVAL_PROMPT_VERSION)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=1), encoding="utf-8")
    DETAILS_DIR.mkdir(parents=True, exist_ok=True)
    (DETAILS_DIR / f"{run_id}.json").write_text(json.dumps(details, indent=1, ensure_ascii=False), encoding="utf-8")
    print("\nSummary")
    for system, s in document["summary"].items():
        hit = "n/a" if s["hit_rate_top10"] is None else f"{s['hit_rate_top10']:.0%} of {s['hit_rows']}"
        made_up = "n/a" if s["made_up_rate"] is None else f"{s['made_up_rate']:.0%} of {s['names_checked']} names"
        emerging = "n/a" if s["emerging_share"] is None else f"{s['emerging_share']:.0%}"
        print(f"  {system:<4} hit@10 {hit} · made-up {made_up} · emerging {emerging} · median {s['median_seconds']}s · ${s['total_usd']} · errors {s['errors']}")
    print(f"\nScores saved to {out}. Suggested names (private, not for the repo) in {DETAILS_DIR}/{run_id}.json")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(asyncio.run(main()))
