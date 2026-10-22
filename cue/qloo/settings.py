from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from cue.qloo.errors import SettingsError

HACKATHON_BASE_URL = "https://hackathon.api.qloo.com"


def _flag(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class QlooSettings:
    api_key: str
    base_url: str = HACKATHON_BASE_URL
    demo_mode: bool = False
    timeout_s: float = 10.0
    max_retries: int = 3
    backoff_base_s: float = 0.5
    rate_per_s: float = 5.0
    burst: int = 10

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> QlooSettings:
        env = os.environ if env is None else env
        demo_mode = _flag(env.get("DEMO_MODE"))
        api_key = env.get("QLOO_API_KEY", "").strip()
        if not api_key and not demo_mode:
            raise SettingsError("QLOO_API_KEY is not set. Add it to .env, or set DEMO_MODE=true.")
        return cls(
            api_key=api_key,
            base_url=env.get("QLOO_BASE_URL", HACKATHON_BASE_URL).rstrip("/"),
            demo_mode=demo_mode,
            rate_per_s=float(env.get("QLOO_RATE_PER_SEC", "5")),
            burst=int(env.get("QLOO_BURST", "10")),
        )
