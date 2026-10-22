from __future__ import annotations

from cue.qloo.params import ENTITIES
from cue.tools.context import qloo_get
from cue.tools.parse import entity, results_list
from cue.tools.records import Entity

BATCH = 50


async def get_entities(ids: list[str]) -> list[Entity]:
    wanted = list(dict.fromkeys(i for i in ids if i))
    found: dict[str, Entity] = {}
    for start in range(0, len(wanted), BATCH):
        batch = wanted[start : start + BATCH]
        data = await qloo_get(ENTITIES, {"entity_ids": batch})
        for raw in results_list(data):
            try:
                record = entity(raw)
            except ValueError:
                continue
            found[record.ref.id] = record
    return [found[i] for i in wanted if i in found]
