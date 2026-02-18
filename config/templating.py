from __future__ import annotations

import copy
import re
from typing import Any

_TOKEN = re.compile(r"\{([a-zA-Z0-9_.-]+)\}")


def get_dotted(mapping: dict[str, Any], dotted: str) -> Any:
    current: Any = mapping
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(dotted)
        current = current[part]
    return current


def set_dotted(mapping: dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    current: dict[str, Any] = mapping
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    current[parts[-1]] = value


def render_template(value: str, scope: dict[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        resolved = get_dotted(scope, key)
        return str(resolved)

    return _TOKEN.sub(replace, value)


def resolve_templates(obj: Any, scope: dict[str, Any]) -> Any:
    if isinstance(obj, str):
        return render_template(obj, scope)
    if isinstance(obj, list):
        return [resolve_templates(item, scope) for item in obj]
    if isinstance(obj, dict):
        return {k: resolve_templates(v, scope) for k, v in obj.items()}
    return copy.deepcopy(obj)
