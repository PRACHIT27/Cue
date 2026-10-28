from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal, Protocol

from cue.qloo.params import ENTITIES
from cue.tools import find_entity, get_entities
from cue.tools.context import qloo_get
from cue.tools.parse import entity, results_list
from cue.tools.records import Entity

ARTIST = "urn:entity:artist"
PERSON = "urn:entity:person"
AUTHOR = "urn:entity:author"
ROLES = ("singer", "band", "producer", "composer", "lyricist")
Route = Literal["spotify", "musicbrainz", "name", "stand_in"]

SPOTIFY_ID = re.compile(r"^[A-Za-z0-9]{22}$")
SPOTIFY_LINK = re.compile(r"(?:spotify\.com/(?:intl-[a-z-]+/)?artist/|spotify:artist:)([A-Za-z0-9]{22})")


class MusicBrainz(Protocol):
    async def find_mbid_for_spotify(self, spotify_id: str, name: str = "") -> str | None: ...


@dataclass(frozen=True)
class Candidate:
    entity_id: str
    name: str
    type: str
    popularity: float
    description: str | None
    image_url: str | None
    listeners: int | None
    spotify_id: str | None
    musicbrainz_id: str | None
    related_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class Onboarding:
    route: Route | None
    candidates: tuple[Candidate, ...] = ()
    note: str = ""
    skipped: tuple[str, ...] = field(default_factory=tuple)


def spotify_id_from(text: str) -> str | None:
    text = (text or "").strip()
    if SPOTIFY_ID.match(text):
        return text
    match = SPOTIFY_LINK.search(text)
    return match.group(1) if match else None


def search_types(role: str) -> list[str]:
    return [PERSON, AUTHOR] if role == "lyricist" else [ARTIST]


async def entities_by_external(source: str, value: str) -> list[Entity]:
    data = await qloo_get(ENTITIES, {f"external.{source}.ids": value})
    found: list[Entity] = []
    for raw in results_list(data):
        try:
            found.append(entity(raw))
        except ValueError:
            continue
    return found


def _rank(record: Entity) -> tuple[int, float]:
    return (0 if record.ref.type == ARTIST else 1, -record.ref.popularity)


def candidate(primary: Entity, related: list[Entity]) -> Candidate:
    return Candidate(
        entity_id=primary.ref.id,
        name=primary.ref.name,
        type=primary.ref.type,
        popularity=primary.ref.popularity,
        description=primary.description,
        image_url=primary.image_url,
        listeners=primary.lastfm_listeners or next((r.lastfm_listeners for r in related if r.lastfm_listeners), None),
        spotify_id=primary.spotify_id or next((r.spotify_id for r in related if r.spotify_id), None),
        musicbrainz_id=primary.musicbrainz_id or next((r.musicbrainz_id for r in related if r.musicbrainz_id), None),
        related_ids=tuple(r.ref.id for r in related if r.ref.id != primary.ref.id),
    )


async def merged(records: list[Entity]) -> Candidate:
    records = sorted(records, key=_rank)
    primary = records[0]
    family = list(records)
    mbid = primary.musicbrainz_id or next((r.musicbrainz_id for r in records if r.musicbrainz_id), None)
    if mbid:
        known = {r.ref.id for r in family}
        family += [r for r in await entities_by_external("musicbrainz", mbid) if r.ref.id not in known]
        family = sorted(family, key=_rank)
        primary = family[0]
    return candidate(primary, family)


async def by_spotify(link: str, musicbrainz: MusicBrainz, name: str = "") -> Onboarding:
    spotify_id = spotify_id_from(link)
    if spotify_id is None:
        return Onboarding(None, note="That doesn't look like a Spotify artist link.")
    direct = await entities_by_external("spotify", spotify_id)
    if direct:
        return Onboarding("spotify", (await merged(direct),))
    mbid = await musicbrainz.find_mbid_for_spotify(spotify_id, name)
    if mbid:
        via_mbid = await entities_by_external("musicbrainz", mbid)
        if via_mbid:
            return Onboarding("musicbrainz", (await merged(via_mbid),))
    return Onboarding(None, note="Qloo doesn't know this Spotify artist yet. Tell us who you sound like instead.")


def _grouped(records: list[Entity]) -> list[list[Entity]]:
    groups: list[list[Entity]] = []
    index: dict[str, int] = {}
    for record in records:
        keys = [k for k in (record.spotify_id and f"s:{record.spotify_id}", record.musicbrainz_id and f"m:{record.musicbrainz_id}") if k]
        slot = next((index[k] for k in keys if k in index), None)
        if slot is None:
            slot = len(groups)
            groups.append([])
        groups[slot].append(record)
        for key in keys:
            index.setdefault(key, slot)
    return groups


async def by_name(name: str, role: str, limit: int = 3) -> Onboarding:
    refs = await find_entity(name, search_types(role))
    if not refs:
        return Onboarding(None, note=f"Qloo has no {'lyricist' if role == 'lyricist' else 'artist'} called {name.strip()!r}.")
    records = await get_entities([r.id for r in refs])
    if not records:
        return Onboarding(None, note=f"Qloo has no details for {name.strip()!r}.")
    candidates = [await merged(group) for group in _grouped(records)][:limit]
    return Onboarding("name", tuple(candidates))


async def by_sounds_like(names: list[str]) -> Onboarding:
    resolved: list[Candidate] = []
    skipped: list[str] = []
    seen: set[str] = set()
    for raw_name in names:
        name = raw_name.strip()
        if not name:
            continue
        refs = await find_entity(name, [ARTIST])
        if len(refs) != 1:
            skipped.append(f"{name}: {'not in Qloo' if not refs else 'more than one artist with that name'}")
            continue
        if refs[0].id in seen:
            continue
        seen.add(refs[0].id)
        records = await get_entities([refs[0].id])
        resolved.append(candidate(records[0], records) if records else Candidate(refs[0].id, refs[0].name, refs[0].type, refs[0].popularity, None, None, None, None, None))
    note = "" if resolved else "None of these artists are in Qloo."
    return Onboarding("stand_in" if resolved else None, tuple(resolved), note, tuple(skipped))
