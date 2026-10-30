from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator

from cue.agents.planner.agent import similar_artists
from cue.api import onboarding
from cue.api.runs import RunManager
from cue.api.serialize import jsonable
from cue.identity.musicbrainz import shared_client
from cue.qloo.cache import InMemoryCache
from cue.qloo.ratelimit import TokenBucket
from cue.qloo.settings import QlooSettings
from cue.qloo.smoke import _load_dotenv
from cue.qloo.params import INSIGHTS
from cue.tools import find_entity, get_entities, insights, use_client
from cue.tools.context import qloo_get
from cue.tools.records import InsightsRequest

PRODUCTION_TYPES = ("tv_show", "movie", "videogame", "podcast", "brand")
LIVE_MUSIC_VENUE = "urn:tag:genre:place:live_music_venue"
Role = Literal["singer", "band", "producer", "composer", "lyricist"]


class SpotifyLookup(BaseModel):
    link: str = Field(min_length=1)
    role: Role = "singer"
    name: str = ""


class NameLookup(BaseModel):
    name: str = Field(min_length=1)
    role: Role = "singer"


class SoundsLike(BaseModel):
    names: list[str] = Field(min_length=1, max_length=5)


class ProductionLookup(BaseModel):
    name: str = Field(min_length=1)
    type: Literal["tv_show", "movie", "videogame", "podcast", "brand"] = "tv_show"


class RunRequest(BaseModel):
    mode: Literal["artist", "supervisor"]
    brief: str = Field(default="", max_length=500)
    signal_ids: list[str] = Field(default_factory=list, max_length=5)
    artist_name: str = ""
    basis: Literal["measured", "projected"] = "measured"
    route: Literal["spotify", "musicbrainz", "name", "stand_in"] | None = None
    production_id: str = ""
    production_name: str = ""
    production_type: Literal["tv_show", "movie", "videogame", "podcast", "brand"] = "tv_show"

    @model_validator(mode="after")
    def check_mode(self) -> RunRequest:
        if self.mode == "artist" and (not self.signal_ids or not self.artist_name.strip()):
            raise ValueError("artist runs need signal_ids and artist_name")
        if self.mode == "supervisor" and (not self.production_id or not self.production_name.strip()):
            raise ValueError("supervisor runs need production_id and production_name")
        return self


def settings_from_env() -> QlooSettings:
    return QlooSettings.from_env({**_load_dotenv(), **os.environ})


def create_app(manager: RunManager | None = None, musicbrainz: Any = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if not hasattr(app.state, "manager"):
            settings = settings_from_env()
            app.state.manager = RunManager(settings, InMemoryCache(), TokenBucket(settings.rate_per_s, settings.burst))
        if not hasattr(app.state, "musicbrainz"):
            app.state.musicbrainz = shared_client()
        yield

    app = FastAPI(title="Cue API", lifespan=lifespan)
    if manager is not None:
        app.state.manager = manager
    if musicbrainz is not None:
        app.state.musicbrainz = musicbrainz
    origins = [o.strip() for o in os.environ.get("CUE_WEB_ORIGINS", "*").split(",") if o.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"], allow_headers=["*"])

    async def with_qloo(work):
        async with app.state.manager.client() as client:
            with use_client(client):
                return await work()

    @app.get("/health")
    async def health() -> dict[str, Any]:
        manager: RunManager = app.state.manager
        return {"ok": True, "demo_mode": manager.settings.demo_mode, "runs": len(manager.runs)}

    @app.post("/onboarding/spotify")
    async def onboarding_spotify(body: SpotifyLookup) -> dict[str, Any]:
        found = await with_qloo(lambda: onboarding.by_spotify(body.link, app.state.musicbrainz, body.name))
        return jsonable(found)

    @app.post("/onboarding/name")
    async def onboarding_name(body: NameLookup) -> dict[str, Any]:
        return jsonable(await with_qloo(lambda: onboarding.by_name(body.name, body.role)))

    @app.post("/onboarding/sounds-like")
    async def onboarding_sounds_like(body: SoundsLike) -> dict[str, Any]:
        return jsonable(await with_qloo(lambda: onboarding.by_sounds_like(body.names)))

    @app.get("/artists/{entity_id}/profile")
    async def artist_profile(entity_id: str) -> dict[str, Any]:
        async def work():
            records = await get_entities([entity_id])
            if not records:
                return None
            demo = await insights(InsightsRequest("urn:demographics", signal_entities=(entity_id,)))
            return records[0], demo.demographics[0] if demo.demographics else None

        found = await with_qloo(work)
        if found is None:
            raise HTTPException(404, "No Qloo entity with that ID")
        record, demographics = found
        tags: dict[str, list[str]] = {}
        for tag in record.tags:
            group = tag.type.split(":")[2] if tag.type.count(":") >= 2 else "other"
            if tag.name not in tags.setdefault(group, []):
                tags[group].append(tag.name)
        return {"entity": jsonable(record), "tags": tags, "demographics": jsonable(demographics)}

    @app.get("/artists/{entity_id}/similar")
    async def artist_similar(entity_id: str) -> dict[str, Any]:
        async def work():
            ids = await similar_artists([entity_id])
            return ids, (await get_entities(ids) if ids else [])

        ids, records = await with_qloo(work)
        by_id = {r.ref.id: r for r in records}
        found = [by_id[i] for i in ids if i in by_id]
        return {"artists": [{"id": r.ref.id, "name": r.ref.name, "image_url": r.image_url, "popularity": r.ref.popularity} for r in found]}

    @app.get("/artists/{entity_id}/venues")
    async def artist_venues(entity_id: str, city: str = "", take: int = 6) -> dict[str, Any]:
        city = city.strip()
        if not city:
            raise HTTPException(422, "Add a city, such as Detroit or Mumbai")
        params = {
            "filter.type": "urn:entity:place",
            "signal.interests.entities": entity_id,
            "filter.location.query": city,
            "filter.tags": LIVE_MUSIC_VENUE,
            "take": max(1, min(take, 12)),
        }
        try:
            data = await with_qloo(lambda: qloo_get(INSIGHTS, params))
        except Exception as failure:
            raise HTTPException(502, f"Qloo couldn't find venues for {city!r}: {failure}")
        venues = []
        for raw in ((data or {}).get("results") or {}).get("entities") or []:
            properties = raw.get("properties") or {}
            venues.append(
                {
                    "id": raw.get("entity_id"),
                    "name": raw.get("name"),
                    "address": properties.get("address"),
                    "affinity": (raw.get("query") or {}).get("affinity"),
                    "popularity": raw.get("popularity"),
                }
            )
        return {"city": city, "venues": venues}

    @app.post("/productions/search")
    async def production_search(body: ProductionLookup) -> dict[str, Any]:
        refs = await with_qloo(lambda: find_entity(body.name, [f"urn:entity:{body.type}"]))
        return {"candidates": jsonable(refs)}

    @app.post("/runs", status_code=202)
    async def start_run(body: RunRequest) -> dict[str, Any]:
        request = body.model_dump()
        if body.mode == "supervisor":
            request["production_type"] = f"urn:entity:{body.production_type}"
        state = app.state.manager.start(body.mode, request)
        return {"run_id": state.run_id, "events": f"/runs/{state.run_id}/events", "result": f"/runs/{state.run_id}"}

    @app.get("/runs/{run_id}")
    async def get_run(run_id: str) -> dict[str, Any]:
        state = app.state.manager.runs.get(run_id)
        if state is None:
            raise HTTPException(404, "No run with that ID; runs are kept for two hours")
        return state.summary()

    @app.get("/runs/{run_id}/events")
    async def run_events(run_id: str) -> StreamingResponse:
        if run_id not in app.state.manager.runs:
            raise HTTPException(404, "No run with that ID; runs are kept for two hours")

        async def body():
            async for event in app.state.manager.stream(run_id):
                yield f"id: {event['seq']}\nevent: {event['kind']}\ndata: {json.dumps(event, default=str)}\n\n"

        return StreamingResponse(body(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    return app


app = create_app()
