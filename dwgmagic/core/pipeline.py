"""Pipeline orchestration for DWGMAGIC."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence

from .context import ProjectContext, StageResult


class PipelineStage:
    """Interface for pipeline stages."""

    name: str

    def run(self, context: ProjectContext) -> StageResult:  # pragma: no cover - interface
        raise NotImplementedError


@dataclass(slots=True)
class PipelineRunner:
    """Sequentially executes pipeline stages, surfacing structured results."""

    stages: Sequence[PipelineStage]

    def run(self, context: ProjectContext) -> List[StageResult]:
        results: List[StageResult] = []
        for stage in self.stages:
            result = stage.run(context)
            results.append(result)
            if not result.succeeded:
                break
        return results

    @classmethod
    def from_iterable(cls, stages: Iterable[PipelineStage]) -> "PipelineRunner":
        return cls(tuple(stages))

