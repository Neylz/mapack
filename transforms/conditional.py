from __future__ import annotations

from .registry import register_transform


def _compare(op: str, a, b) -> bool:
    match op:
        case "==":
            return a == b
        case "!=":
            return a != b
        case ">":
            return a > b
        case ">=":
            return a >= b
        case "<":
            return a < b
        case "<=":
            return a <= b
        case _:
            raise ValueError(f"Unsupported conditional op: {op}")


def _run_transform_or_list(ctx, block):
    if block is None:
        return
    if isinstance(block, list):
        for item in block:
            ctx.run_nested_transform(item)
        return
    if isinstance(block, dict):
        ctx.run_nested_transform(block)
        return
    raise ValueError("conditional transform expects dict or list for then/else")


@register_transform("conditional")
def transform_conditional(ctx, spec: dict) -> None:
    op = str(spec.get("op", "=="))
    a = ctx.resolve_expr_or_value(spec.get("a"))
    b = ctx.resolve_expr_or_value(spec.get("b"))
    if _compare(op, a, b):
        _run_transform_or_list(ctx, spec.get("then"))
    else:
        _run_transform_or_list(ctx, spec.get("else"))
