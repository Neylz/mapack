from __future__ import annotations

import shutil
from pathlib import Path

from .registry import register_transform


_DIMENSION_PATHS = {
    "minecraft:the_nether": [
        ["DIM-1"],
        ["dimensions", "minecraft", "the_nether"],
    ],
    "minecraft:the_end": [
        ["DIM1"],
        ["dimensions", "minecraft", "the_end"],
    ],
}


def _remove_dimension_folders(workdir: Path, keep: set[str]) -> None:
    for dim, folders in _DIMENSION_PATHS.items():
        if dim in keep:
            continue
        for parts in folders:
            path = workdir.joinpath(*parts)
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)


@register_transform("mc:feature")
def transform_mc_feature(ctx, spec: dict) -> None:
    feature = str(ctx.resolve_value(spec.get("feature", "")))
    args = spec.get("args") or {}
    if not isinstance(args, dict):
        raise ValueError("mc:feature args must be an object")

    if feature == "delete_dimensions":
        keep_raw = args.get("keep", ["minecraft:overworld"])
        if not isinstance(keep_raw, list):
            raise ValueError("mc:feature delete_dimensions args.keep must be a list")
        keep = {str(ctx.resolve_value(v)) for v in keep_raw}
        _remove_dimension_folders(ctx.workdir, keep)
        return

    raise ValueError(f"Unsupported mc:feature value: {feature}")
