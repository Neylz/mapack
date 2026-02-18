from __future__ import annotations

from typing import Any

from .base import TransformHandler


class TransformRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, TransformHandler] = {}

    def register(self, name: str, handler: TransformHandler) -> None:
        key = name.strip()
        if not key:
            raise ValueError("Transform name cannot be empty")
        self._handlers[key] = handler

    def get(self, name: str) -> TransformHandler:
        if name not in self._handlers:
            raise KeyError(f"Unknown transform type: {name}")
        return self._handlers[name]

    def names(self) -> list[str]:
        return sorted(self._handlers.keys())


registry = TransformRegistry()


def register_transform(name: str):
    def wrapper(func: TransformHandler) -> TransformHandler:
        registry.register(name, func)
        return func

    return wrapper


def run_transform(name: str, ctx: Any, spec: dict[str, Any]) -> None:
    handler = registry.get(name)
    handler(ctx, spec)
