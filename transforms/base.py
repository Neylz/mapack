from __future__ import annotations

from typing import Any, Protocol


class TransformContextProtocol(Protocol):
    def run_nested_transform(self, spec: dict[str, Any]) -> None: ...


class TransformHandler(Protocol):
    def __call__(self, ctx: TransformContextProtocol, spec: dict[str, Any]) -> None: ...
