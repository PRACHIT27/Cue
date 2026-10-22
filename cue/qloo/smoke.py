from __future__ import annotations

import asyncio
import json
import os
import sys

from cue.qloo.client import QlooClient
from cue.qloo.params import SEARCH
from cue.qloo.settings import QlooSettings


def _load_dotenv(path: str = ".env") -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    name, value = line.split("=", 1)
                    values[name.strip()] = value.strip()
    except FileNotFoundError:
        pass
    return values


async def main(name: str) -> None:
    settings = QlooSettings.from_env({**_load_dotenv(), **os.environ})
    events = []
    async with QlooClient(settings, sink=events.append) as client:
        data = await client.get(SEARCH, {"query": name, "take": 3})
    for item in data.get("results", [])[:3]:
        print(f"{item.get('name')}  {item.get('entity_id')}  popularity={item.get('popularity')}")
    print(json.dumps(events[-1].to_dict(), indent=2))


if __name__ == "__main__":
    asyncio.run(main(" ".join(sys.argv[1:]) or "Prateek Kuhad"))
