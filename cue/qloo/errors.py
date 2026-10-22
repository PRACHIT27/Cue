from __future__ import annotations


class QlooError(Exception):
    pass


class ParamRejected(QlooError):
    def __init__(self, endpoint: str, reasons: list[str]) -> None:
        self.endpoint = endpoint
        self.reasons = reasons
        super().__init__(f"{endpoint}: " + "; ".join(reasons))


class QlooHTTPError(QlooError):
    def __init__(self, endpoint: str, status: int | None, message: str) -> None:
        self.endpoint = endpoint
        self.status = status
        super().__init__(f"{endpoint}: {status} {message}")


class DemoCacheMiss(QlooError):
    def __init__(self, endpoint: str, params: dict[str, str]) -> None:
        self.endpoint = endpoint
        self.params = params
        super().__init__(f"DEMO_MODE is on and {endpoint} is not cached for {params}")


class SettingsError(QlooError):
    pass
