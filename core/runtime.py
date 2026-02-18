from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ArtifactResult:
    name: str
    workdir: Path
    output_path: Path | None = None


@dataclass(slots=True)
class InterpreterState:
    config_path: Path
    target_name: str
    scope: dict[str, Any]
    artifact_results: dict[str, ArtifactResult] = field(default_factory=dict)

    @property
    def config_dir(self) -> Path:
        return self.config_path.parent
