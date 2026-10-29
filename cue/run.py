from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import asdict, is_dataclass
from typing import Any

from cue.agents.artist_run import run_artist
from cue.agents.common.llm import Budget
from cue.agents.supervisor_run import SHORTLIST_LABEL, run_supervisor
from cue.harness.events import RunEvents
from cue.qloo.client import QlooClient
from cue.qloo.settings import QlooSettings
from cue.qloo.smoke import _load_dotenv
from cue.tools import find_entity, use_client

ARTIST = "urn:entity:artist"
PRODUCTION_TYPES = ["tv_show", "movie", "videogame", "podcast", "brand"]
SECTION_TITLES = {"big_screen": "Big screen", "prime_time": "Prime time", "indie_gems": "Indie gems"}


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


async def _resolve(name: str, types: list[str]) -> list:
    return await find_entity(name, types)


def _print_trace(events: list[dict[str, Any]]) -> None:
    print("\nTrace")
    for e in events:
        if e["kind"] == "qloo_call":
            print(f"  {e['seq']:>3} qloo  {e['endpoint']:<22} {e['cache']:<5} {e['status']:<6} {e['ms']:>5} ms")
        elif e["kind"] in ("step_start", "step_end"):
            note = f"  {e['note']}" if e.get("note") else ""
            print(f"  {e['seq']:>3} {e['kind']:<10} {e.get('step', '')}{' ' + e['status'] if e.get('status') else ''}{note}")
        elif e["kind"] == "guard_drop":
            print(f"  {e['seq']:>3} dropped   [{e['guard']}] {e['text'][:60]}: {e['reason']}")
        else:
            print(f"  {e['seq']:>3} {e['kind']}")


async def artist_mode(args: argparse.Namespace, events: RunEvents) -> Any:
    found = await _resolve(args.name, [ARTIST])
    basis = "measured"
    if args.entity_id:
        signal_ids = [args.entity_id]
    elif len(found) == 1:
        signal_ids = [found[0].id]
    elif len(found) > 1:
        print(f"Several artists are called {args.name!r}. Run again with --entity-id:")
        for ref in found:
            print(f"  {ref.id}  popularity {ref.popularity:.2f}")
        return None
    else:
        sounds_like = [s.strip() for s in (args.sounds_like or "").split(",") if s.strip()]
        if not sounds_like:
            print(f"{args.name!r} isn't in Qloo. Run again with --sounds-like \"Artist A, Artist B\".")
            return None
        signal_ids = []
        for comparable in sounds_like:
            refs = await _resolve(comparable, [ARTIST])
            if len(refs) == 1:
                signal_ids.append(refs[0].id)
            else:
                print(f"  skipped sounds-like {comparable!r}: {'not found' if not refs else 'more than one match'}")
        if not signal_ids:
            print("None of the sounds-like artists were found in Qloo.")
            return None
        basis = "projected"
    run = await run_artist(signal_ids, args.name, events, brief=args.brief, basis=basis)
    print(f"\n{args.name} ({basis}) · {len(run.matches)} productions scored · {len(run.kit.items)} pitches")
    for section in SECTION_TITLES:
        items = [i for i in run.kit.items if i.fit.inputs.get("section") == section]
        if not items:
            continue
        print(f"\n{SECTION_TITLES[section]}")
        for item in items:
            kind = item.candidate.type.split(":")[-1].replace("_", " ")
            label = BASIS_LABELS.get(item.fit.inputs.get("basis"), "")
            print(f"  {item.candidate.name} ({kind})  fit {item.fit.value:.2f}{'  [' + label + ']' if label else ''}")
            print(f"    {item.reason}")
            if args.emails:
                print(f"    Subject: {item.email_subject}\n    {item.email_body}")
    return run


BASIS_LABELS = {"audience_only": "audience match only", "weak": "weak match"}


async def supervisor_mode(args: argparse.Namespace, events: RunEvents) -> Any:
    production_type = f"urn:entity:{args.production_type}"
    if args.entity_id:
        production_id, production_name = args.entity_id, args.name
    else:
        found = await _resolve(args.name, [production_type])
        if len(found) != 1:
            print(f"{'No' if not found else 'More than one'} {args.production_type} called {args.name!r}. Check --type, or pass --entity-id.")
            for ref in found:
                print(f"  {ref.id}  popularity {ref.popularity:.2f}")
            return None
        production_id, production_name = found[0].id, found[0].name
    run = await run_supervisor(production_id, production_name, production_type, events, brief=args.brief)
    print(f"\n{SHORTLIST_LABEL} for {production_name} · cap {run.cap:.2f} · {len(run.brief.artists)} artists")
    for item in run.brief.artists:
        inputs = item.fit.inputs
        print(f"  {item.candidate.name}  fit {item.fit.value:.2f}  ({inputs.get('life_span')})  {inputs.get('spotify_url') or ''}")
        print(f"    {item.reason}")
    return run


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m cue.run", description="Run Cue end to end from the command line.")
    p.add_argument("mode", choices=["artist", "supervisor"])
    p.add_argument("name", help="the artist's name, or the production's name")
    p.add_argument("--brief", default="", help="what the music is for, in plain words")
    p.add_argument("--sounds-like", help="artist mode: comma-separated artists, for an artist Qloo doesn't know")
    p.add_argument("--type", dest="production_type", default="tv_show", choices=PRODUCTION_TYPES, help="supervisor mode: the production's type")
    p.add_argument("--entity-id", help="use this Qloo ID instead of searching by name")
    p.add_argument("--emails", action="store_true", help="artist mode: print the full pitch emails")
    p.add_argument("--trace", action="store_true", help="print every step and Qloo call")
    p.add_argument("--json", dest="json_path", help="also save the full result as JSON to this file")
    return p


async def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    log: list[dict[str, Any]] = []
    run_id = f"cli_{int(time.time())}"
    events = RunEvents(run_id, log.append)
    budget = Budget.from_env()
    before = budget.spent()
    started = time.perf_counter()
    async with QlooClient(QlooSettings.from_env({**_load_dotenv(), **os.environ}), sink=events.qloo_sink) as client:
        with use_client(client, run_id=run_id):
            run = await (artist_mode(args, events) if args.mode == "artist" else supervisor_mode(args, events))
    if args.trace:
        _print_trace(log)
    if run is not None and args.json_path:
        with open(args.json_path, "w", encoding="utf-8") as handle:
            json.dump({"result": _jsonable(run), "events": log}, handle, indent=1, ensure_ascii=False)
        print(f"\nSaved to {args.json_path}")
    calls = sum(1 for e in log if e["kind"] == "qloo_call")
    print(f"\n{time.perf_counter() - started:.1f} s · {calls} Qloo calls · Claude ${budget.spent() - before:.4f} this run, ${budget.spent():.4f} of ${budget.limit_usd:.2f} total")
    return 0 if run is not None else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(asyncio.run(main()))
