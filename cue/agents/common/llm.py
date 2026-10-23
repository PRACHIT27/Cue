from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

PRICES_PER_MTOK = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
}
CHARS_PER_TOKEN = 3.0
CACHE_DIR = Path(".cache/llm")
LEDGER = Path(".cache/llm_spend.json")


class LLMError(RuntimeError):
    pass


class BudgetExceeded(LLMError):
    pass


class DemoLLMMiss(LLMError):
    pass


def _env(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    if value is not None:
        return value.strip()
    try:
        for line in Path(".env").read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip()
    except FileNotFoundError:
        pass
    return default


def price(model: str) -> tuple[float, float]:
    if model not in PRICES_PER_MTOK:
        raise LLMError(f"no price known for {model}; add it to PRICES_PER_MTOK before using it")
    return PRICES_PER_MTOK[model]


def cost(model: str, input_tokens: int, output_tokens: int) -> float:
    price_in, price_out = price(model)
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000


@dataclass
class Budget:
    limit_usd: float
    ledger: Path = LEDGER

    @classmethod
    def from_env(cls) -> Budget:
        return cls(float(_env("LLM_BUDGET_USD", "0") or 0))

    def _read(self) -> dict[str, Any]:
        try:
            return json.loads(self.ledger.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {"entries": []}

    def spent(self) -> float:
        return round(sum(e.get("usd", 0.0) for e in self._read().get("entries", [])), 6)

    def check(self, worst_case_usd: float) -> None:
        if self.limit_usd <= 0:
            raise BudgetExceeded("LLM_BUDGET_USD is not set; refusing to call a paid model")
        if self.spent() + worst_case_usd > self.limit_usd:
            raise BudgetExceeded(
                f"this call could cost up to ${worst_case_usd:.4f}; spent ${self.spent():.4f} of ${self.limit_usd:.2f}"
            )

    def record(self, label: str, model: str, input_tokens: int, output_tokens: int) -> float:
        usd = round(cost(model, input_tokens, output_tokens), 6)
        data = self._read()
        data.setdefault("entries", []).append(
            {"when": time.strftime("%Y-%m-%d %H:%M"), "what": label, "model": model, "input_tokens": input_tokens, "output_tokens": output_tokens, "usd": usd}
        )
        data["budget_usd"] = self.limit_usd
        data["spent_usd"] = round(sum(e["usd"] for e in data["entries"]), 6)
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        self.ledger.write_text(json.dumps(data, indent=1), encoding="utf-8")
        return usd


def _key(model: str, system: str, user: str, schema: Mapping[str, Any], prompt_version: str) -> str:
    body = json.dumps({"m": model, "v": prompt_version, "s": system, "u": user, "f": schema}, sort_keys=True)
    return hashlib.sha256(body.encode()).hexdigest()


def _default_client() -> Any:
    import anthropic

    key = _env("LLM_API_KEY")
    if not key:
        raise LLMError("LLM_API_KEY is not set in .env")
    return anthropic.AsyncAnthropic(api_key=key)


async def structured(
    *,
    label: str,
    system: str,
    user: str,
    schema: Mapping[str, Any],
    prompt_version: str,
    model: str | None = None,
    max_tokens: int = 2000,
    effort: str = "low",
    budget: Budget | None = None,
    client_factory: Callable[[], Any] = _default_client,
    demo_mode: bool | None = None,
) -> dict[str, Any]:
    model = model or _env("LLM_SMALL_MODEL", "claude-haiku-5-5")
    demo_mode = _env("DEMO_MODE").lower() in {"1", "true", "yes"} if demo_mode is None else demo_mode
    key = _key(model, system, user, schema, prompt_version)
    cached = CACHE_DIR / f"{key}.json"
    if cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))
    if demo_mode:
        raise DemoLLMMiss(f"DEMO_MODE is on and {label} is not cached")

    budget = budget or Budget.from_env()
    worst = cost(model, int(len(system + user + json.dumps(schema)) / CHARS_PER_TOKEN), max_tokens)
    budget.check(worst)

    response = await client_factory().messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": dict(schema)}},
    )
    budget.record(label, model, response.usage.input_tokens, response.usage.output_tokens)
    if response.stop_reason == "refusal":
        raise LLMError(f"{label}: the model declined")
    if response.stop_reason == "max_tokens":
        raise LLMError(f"{label}: ran out of max_tokens before finishing")
    text = next((b.text for b in response.content if b.type == "text"), "")
    try:
        result = json.loads(text)
    except json.JSONDecodeError as failure:
        raise LLMError(f"{label}: output was not valid JSON") from failure
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(result), encoding="utf-8")
    return result
