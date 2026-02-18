from __future__ import annotations

import logging

from .registry import register_transform

logger = logging.getLogger("mapack")


@register_transform("log")
def transform_log(ctx, spec: dict) -> None:
    message = ctx.resolve_value(spec.get("message", ""))
    logger.info("[transform:log] %s", message)
