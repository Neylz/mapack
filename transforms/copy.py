from __future__ import annotations

import shutil
from pathlib import Path

from .registry import register_transform


def _copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _copy_tree_contents(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for child in src.iterdir():
        target = dst / child.name
        if child.is_dir():
            shutil.copytree(child, target, dirs_exist_ok=True)
        else:
            _copy_file(child, target)


@register_transform("copy")
def transform_copy(ctx, spec: dict) -> None:
    src = ctx.resolve_source(spec.get("src"), allow_artifact_output=True)
    dest_rel = str(ctx.resolve_value(spec.get("dest", ".")))
    dest = (ctx.workdir / dest_rel).resolve()

    if not src.exists():
        raise FileNotFoundError(f"copy transform source does not exist: {src}")

    if src.is_file():
        if dest.exists() and dest.is_dir():
            _copy_file(src, dest / src.name)
        else:
            _copy_file(src, dest)
        return

    # directory source
    if dest.exists() and dest.is_file():
        raise ValueError(f"Cannot copy directory into file: {dest}")

    _copy_tree_contents(src, dest)
