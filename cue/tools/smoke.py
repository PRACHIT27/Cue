from __future__ import annotations

import asyncio
import os
import sys

from cue.qloo.client import QlooClient
from cue.qloo.settings import QlooSettings
from cue.qloo.smoke import _load_dotenv
from cue.tools import (
    compare,
    find_audiences,
    find_entity,
    find_tags,
    get_audience_types,
    get_entities,
    get_tag_types,
    insights,
    trend_score,
    trending,
    use_client,
)
from cue.tools.records import InsightsRequest

ARTIST = "urn:entity:artist"
TV = "urn:entity:tv_show"


async def main(name: str) -> None:
    settings = QlooSettings.from_env({**_load_dotenv(), **os.environ})
    events = []
    async with QlooClient(settings, sink=events.append) as client:
        with use_client(client, run_id="smoke"):
            artists = await find_entity(name, [ARTIST])
            print(f"find_entity: {len(artists)} match(es)", [(a.name, round(a.popularity, 2)) for a in artists])
            if not artists:
                return
            artist = artists[0]
            profile = (await get_entities([artist.id]))[0]
            print(f"get_entities: spotify={bool(profile.spotify_id)} lastfm_listeners={profile.lastfm_listeners} tags={len(profile.tags)}")
            bands = {"big screen": (0.90, None), "prime time": (0.70, 0.90), "indie gems": (None, 0.70)}
            requests = {
                label: InsightsRequest(TV, (artist.id,), popularity_min=low, popularity_max=high, take=5)
                for label, (low, high) in bands.items()
            }
            results = await asyncio.gather(*(insights(r) for r in requests.values()))
            for label, result in zip(requests, results):
                print(f"insights {label}: {[(i.rank, i.candidate.name, round(i.candidate.popularity, 2)) for i in result.items]}")
            top = results[0].items[0].candidate if results[0].items else None
            demo = await insights(InsightsRequest("urn:demographics", (artist.id,)))
            print(f"insights demographics: {len(demo.demographics)} block(s)")
            taste = await insights(InsightsRequest("urn:tag", (artist.id,)))
            print(f"insights tags: {len(taste.tags)}")
            heat = await insights(InsightsRequest("urn:heatmap", (artist.id,), filters={"filter.location.query": "Mumbai"}))
            print(f"insights heatmap: {len(heat.heatmap)} point(s)")
            game = await insights(InsightsRequest("urn:entity:videogame", (artist.id,), take=3))
            print(f"insights games (capped): {[(i.candidate.name, round(i.candidate.popularity, 2)) for i in game.items]}")
            if top:
                pair = await compare([artist.id], [top.id])
                print(f"compare vs {top.name}: shared={len(pair.shared)} a_tags={len(pair.a_tags)} b_tags={len(pair.b_tags)}")
                series = await trending(top.id, TV)
                print(f"trending {top.name}: weeks={len(series.weeks)} as_of={series.as_of} score={trend_score(series)}")
            print(f"find_tags: {[t.name for t in await find_tags('dream pop')][:3]}")
            print(f"get_tag_types: {len(await get_tag_types())}")
            print(f"find_audiences: {[a.name for a in await find_audiences('music')][:3]}")
            print(f"get_audience_types: {len(await get_audience_types())}")
    failed = [e for e in events if e.status != "ok"]
    print(f"{len(events)} Qloo calls, {len(failed)} not ok")
    for event in failed:
        print(f"  {event.endpoint} {event.status}: {event.error}")


if __name__ == "__main__":
    asyncio.run(main(" ".join(sys.argv[1:]) or "Prateek Kuhad"))
