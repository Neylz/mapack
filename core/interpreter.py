from __future__ import annotations

import copy
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from config.expressions import ExpressionContext, evaluate_expression
from config.templating import render_template, resolve_templates, set_dotted
from transforms import load_builtin_transforms
from transforms.registry import run_transform
from .runtime import ArtifactResult, InterpreterState

logger = logging.getLogger("mapack")


@dataclass(slots=True)
class TransformContext:
    interpreter: "ConfigInterpreter"
    state: InterpreterState
    artifact_name: str
    workdir: Path

    def resolve_value(self, value: Any) -> Any:
        return self.interpreter._resolve_value(value, self.state)

    def resolve_expr_or_value(self, value: Any) -> Any:
        return self.interpreter._resolve_expr_or_value(value, self.state, self.workdir)

    def resolve_source(self, source_spec: Any, *, allow_artifact_output: bool) -> Path:
        return self.interpreter._resolve_source(source_spec, self.state, allow_artifact_output=allow_artifact_output)

    def run_nested_transform(self, spec: dict[str, Any]) -> None:
        self.interpreter._run_transform(spec, self.state, self.artifact_name, self.workdir)


class ConfigInterpreter:
    def __init__(self, config: dict[str, Any], config_path: Path) -> None:
        self.config = config
        self.config_path = config_path.resolve()
        load_builtin_transforms()

    def run(self, targets: list[str] | None = None, *, dry_run: bool = False) -> dict[str, list[Path]]:
        available_targets = self._get_targets()
        selected = targets or list(available_targets.keys())

        outputs_by_target: dict[str, list[Path]] = {}
        for target_name in selected:
            if target_name not in available_targets:
                raise KeyError(f"Unknown target: {target_name}")

            merged_target = self._materialize_target(target_name)
            state = self._build_state_for_target(target_name, merged_target)
            outputs_by_target[target_name] = self._execute_target(state, merged_target, dry_run=dry_run)

        return outputs_by_target

    def _execute_target(self, state: InterpreterState, target_config: dict[str, Any], *, dry_run: bool) -> list[Path]:
        artifacts = target_config.get("artifacts")
        if not isinstance(artifacts, dict):
            raise ValueError("target.artifacts must be an object")

        requested: list[str] = []
        for name, spec in artifacts.items():
            if not isinstance(spec, dict):
                continue
            export = spec.get("export") or {}
            if isinstance(export, dict) and export.get("enabled", False):
                requested.append(name)

        produced: list[Path] = []
        with TemporaryDirectory(prefix=f"mapack-{state.target_name}-") as tmpdir:
            tmp_root = Path(tmpdir)
            for artifact_name in requested:
                result = self._build_artifact(
                    artifact_name,
                    state=state,
                    target_artifacts=artifacts,
                    temp_root=tmp_root,
                    dry_run=dry_run,
                )
                if result.output_path:
                    produced.append(result.output_path)

        return produced

    def _build_artifact(
        self,
        artifact_name: str,
        *,
        state: InterpreterState,
        target_artifacts: dict[str, Any],
        temp_root: Path,
        dry_run: bool,
    ) -> ArtifactResult:
        existing = state.artifact_results.get(artifact_name)
        if existing is not None:
            return existing

        if artifact_name not in target_artifacts:
            raise KeyError(f"Unknown artifact: {artifact_name}")

        artifact_spec = target_artifacts[artifact_name]
        if not isinstance(artifact_spec, dict):
            raise ValueError(f"Artifact '{artifact_name}' definition must be an object")

        depends_on = artifact_spec.get("depends_on", [])
        if depends_on is None:
            depends_on = []
        if not isinstance(depends_on, list):
            raise ValueError(f"Artifact '{artifact_name}' depends_on must be a list")

        for dep in depends_on:
            dep_name = str(dep)
            self._build_artifact(dep_name, state=state, target_artifacts=target_artifacts, temp_root=temp_root, dry_run=dry_run)

        workdir = temp_root / artifact_name
        workdir.mkdir(parents=True, exist_ok=True)
        result = ArtifactResult(name=artifact_name, workdir=workdir)
        state.artifact_results[artifact_name] = result

        if not dry_run:
            src_spec = artifact_spec.get("src")
            if src_spec is not None:
                src_path = self._resolve_source(src_spec, state, allow_artifact_output=False)
                self._copy_source_to_artifact_root(src_path, workdir)

            for transform in artifact_spec.get("transforms", []):
                self._run_transform(transform, state, artifact_name, workdir)
        else:
            logger.info("artifact=%s dry-run: skipped source copy and transforms", artifact_name)

        export = artifact_spec.get("export")
        if isinstance(export, dict) and export.get("enabled", False):
            resolved_export = self._resolve_value(export, state)
            if not isinstance(resolved_export, dict):
                raise ValueError(f"Artifact '{artifact_name}' export must resolve to object")

            dest_raw = resolved_export.get("dest")
            if not isinstance(dest_raw, str):
                raise ValueError(f"Artifact '{artifact_name}' export.dest must be a string")
            dest_path = self._resolve_path(dest_raw)

            zipped = bool(resolved_export.get("zipped", True))
            if not dry_run:
                if zipped:
                    self._zip_directory(workdir, dest_path)
                else:
                    if dest_path.exists():
                        shutil.rmtree(dest_path, ignore_errors=True)
                    shutil.copytree(workdir, dest_path, dirs_exist_ok=True)
            result.output_path = dest_path
            logger.info("artifact=%s exported -> %s", artifact_name, dest_path)
        else:
            logger.info("artifact=%s built (no export)", artifact_name)

        return result

    def _run_transform(self, spec: dict[str, Any], state: InterpreterState, artifact_name: str, workdir: Path) -> None:
        if not isinstance(spec, dict):
            raise ValueError(f"Transform in '{artifact_name}' must be an object")
        transform_type = spec.get("type")
        if not isinstance(transform_type, str):
            raise ValueError(f"Transform in '{artifact_name}' missing string field 'type'")

        resolved_spec = self._resolve_value(spec, state)
        if not isinstance(resolved_spec, dict):
            raise ValueError("Resolved transform spec must be an object")

        logger.info("artifact=%s transform=%s id=%s", artifact_name, transform_type, resolved_spec.get("id"))
        ctx = TransformContext(interpreter=self, state=state, artifact_name=artifact_name, workdir=workdir)
        run_transform(transform_type, ctx, resolved_spec)

    def _copy_source_to_artifact_root(self, src_path: Path, workdir: Path) -> None:
        if not src_path.exists():
            raise FileNotFoundError(f"Artifact source does not exist: {src_path}")

        if src_path.is_file():
            shutil.copy2(src_path, workdir / src_path.name)
            return

        for child in src_path.iterdir():
            dest = workdir / child.name
            if child.is_dir():
                shutil.copytree(child, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(child, dest)

    def _resolve_source(self, source_spec: Any, state: InterpreterState, *, allow_artifact_output: bool) -> Path:
        resolved = self._resolve_value(source_spec, state)

        if isinstance(resolved, str):
            return self._resolve_path(resolved)

        if isinstance(resolved, dict):
            artifact_ref = resolved.get("artifact")
            if artifact_ref is not None:
                ref_name = str(artifact_ref)
                if ref_name not in state.artifact_results:
                    raise KeyError(f"Referenced artifact has not been built yet: {ref_name}")
                ref = state.artifact_results[ref_name]
                wants_output = bool(resolved.get("output", False))
                if wants_output:
                    if not allow_artifact_output:
                        raise ValueError("This source location does not allow artifact output references")
                    if ref.output_path is None:
                        raise ValueError(f"Artifact '{ref_name}' has no output to reference")
                    return ref.output_path
                return ref.workdir

            if "path" in resolved and isinstance(resolved["path"], str):
                return self._resolve_path(resolved["path"])

        raise ValueError(f"Unsupported source spec: {source_spec}")

    def _resolve_path(self, value: str) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        return (self.config_path.parent / path).resolve()

    def _resolve_expr_or_value(self, value: Any, state: InterpreterState, cwd: Path) -> Any:
        resolved = self._resolve_value(value, state)
        if not isinstance(resolved, str):
            return resolved

        try:
            return evaluate_expression(resolved, context=ExpressionContext(cwd=cwd))
        except Exception:
            return resolved

    def _resolve_value(self, value: Any, state: InterpreterState) -> Any:
        return resolve_templates(value, state.scope)

    def _build_state_for_target(self, target_name: str, target_config: dict[str, Any]) -> InterpreterState:
        variables = target_config.get("variables")
        if not isinstance(variables, dict):
            raise ValueError(f"target '{target_name}' missing object field: variables")

        scope: dict[str, Any] = copy.deepcopy(variables)

        precomputed = target_config.get("precomputed_vars", {})
        if not isinstance(precomputed, dict):
            raise ValueError(f"target '{target_name}' precomputed_vars must be an object")

        for dotted_key, raw_value in precomputed.items():
            if not isinstance(dotted_key, str):
                raise ValueError("precomputed_vars keys must be strings")
            if not isinstance(raw_value, str):
                set_dotted(scope, dotted_key, raw_value)
                continue
            rendered = render_template(raw_value, scope)
            set_dotted(scope, dotted_key, rendered)

        return InterpreterState(config_path=self.config_path, target_name=target_name, scope=scope)

    def _materialize_target(self, target_name: str) -> dict[str, Any]:
        globals_obj = self.config.get("globals", {})
        targets = self._get_targets()
        target_obj = targets[target_name]

        use_global = target_obj.get("use_global", {})
        merged: dict[str, Any]
        if isinstance(use_global, dict) and use_global.get("use_all", False):
            merged = copy.deepcopy(globals_obj)
        else:
            merged = {}

        target_without_use_global = {k: v for k, v in target_obj.items() if k != "use_global"}
        merged = self._deep_merge(merged, target_without_use_global)

        artifacts = merged.get("artifacts")
        if isinstance(artifacts, dict):
            for artifact_name, artifact_spec in list(artifacts.items()):
                if not isinstance(artifact_spec, dict):
                    continue
                artifacts[artifact_name] = self._apply_mod_transforms(artifact_spec)

        return merged

    def _apply_mod_transforms(self, artifact_spec: dict[str, Any]) -> dict[str, Any]:
        out = copy.deepcopy(artifact_spec)
        mod_ops = out.pop("mod_transforms", None)
        if not mod_ops:
            return out

        transforms = out.get("transforms", [])
        if not isinstance(transforms, list):
            raise ValueError("artifact.transforms must be a list")

        for op in mod_ops:
            if not isinstance(op, dict):
                raise ValueError("mod_transforms entries must be objects")
            action = op.get("op")
            ref = op.get("ref")
            transform = op.get("transform")
            if not isinstance(ref, str):
                raise ValueError("mod_transforms.ref must be a string")

            idx = next((i for i, t in enumerate(transforms) if isinstance(t, dict) and t.get("id") == ref), None)
            if idx is None:
                raise ValueError(f"mod_transforms ref not found: {ref}")

            if action == "replace":
                if not isinstance(transform, dict):
                    raise ValueError("mod_transforms.replace requires object transform")
                transforms[idx] = transform
            elif action == "insert":
                if not isinstance(transform, dict):
                    raise ValueError("mod_transforms.insert requires object transform")
                transforms.insert(idx + 1, transform)
            elif action in {"remove", "delete"}:
                transforms.pop(idx)
            else:
                raise ValueError(f"Unsupported mod_transforms op: {action}")

        out["transforms"] = transforms
        return out

    def _deep_merge(self, base: Any, override: Any) -> Any:
        if isinstance(base, dict) and isinstance(override, dict):
            merged = copy.deepcopy(base)
            for key, value in override.items():
                if key in merged:
                    merged[key] = self._deep_merge(merged[key], value)
                else:
                    merged[key] = copy.deepcopy(value)
            return merged
        return copy.deepcopy(override)

    def _get_targets(self) -> dict[str, Any]:
        targets = self.config.get("targets")
        if not isinstance(targets, dict):
            raise ValueError("config.targets must be an object")
        return targets

    def _zip_directory(self, source_dir: Path, zip_path: Path) -> None:
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        if zip_path.suffix.lower() == ".zip":
            base_name = zip_path.with_suffix("")
        else:
            base_name = zip_path
            zip_path = zip_path.with_suffix(".zip")
        shutil.make_archive(str(base_name), "zip", root_dir=source_dir)
