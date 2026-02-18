from __future__ import annotations

import subprocess

from .registry import register_transform


def _run_git(args: list[str], cwd) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), check=True)


@register_transform("git:clone")
def transform_git_clone(ctx, spec: dict) -> None:
    repo_url = str(ctx.resolve_value(spec.get("repo_url")))
    branch = spec.get("branch")
    dest_rel = str(ctx.resolve_value(spec.get("dest", ".")))
    dest = (ctx.workdir / dest_rel).resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)

    args = ["clone"]
    if branch:
        args.extend(["--branch", str(ctx.resolve_value(branch))])
    if dest_rel in {"", "."}:
        args.extend([repo_url, "."])
    else:
        args.extend([repo_url, str(dest)])
    _run_git(args, cwd=ctx.workdir)


@register_transform("git:pull")
def transform_git_pull(ctx, spec: dict) -> None:
    repo_dir_rel = str(ctx.resolve_value(spec.get("repo_dir", ".")))
    branch = spec.get("branch")
    repo_dir = (ctx.workdir / repo_dir_rel).resolve()
    catch = spec.get("catch")

    args = ["pull"]
    if branch:
        args.extend(["origin", str(ctx.resolve_value(branch))])

    try:
        _run_git(args, cwd=repo_dir)
    except Exception:
        if catch is None:
            raise
        ctx.run_nested_transform(catch)
