from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

from cue.qloo import QlooClient

_client: ContextVar[QlooClient | None] = ContextVar("qloo_client", default=None)
_run_id: ContextVar[str | None] = ContextVar("run_id", default=None)


@contextmanager
def use_client(client: QlooClient, run_id: str | None = None) -> Iterator[QlooClient]:
    client_token = _client.set(client)
    run_token = _run_id.set(run_id)
    try:
        yield client
    finally:
        _client.reset(client_token)
        _run_id.reset(run_token)


def current_client() -> QlooClient:
    client = _client.get()
    if client is None:
        raise RuntimeError("No Qloo client in context. Wrap the call in `with use_client(client):`.")
    return client


def current_run_id() -> str | None:
    return _run_id.get()


async def qloo_get(endpoint: str, params: dict) -> dict:
    return await current_client().get(endpoint, params, run_id=current_run_id())
