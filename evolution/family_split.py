"""Shared family split representation for benchmark runners."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FamilySplit:
    """Training, held-out, and optional probe tasks for one family."""

    family_name: str
    acquisition: list[Path] = field(default_factory=list)
    deployment: list[Path] = field(default_factory=list)
    probe: list[Path] = field(default_factory=list)

    @property
    def all_tasks(self) -> list[Path]:
        return self.acquisition + self.deployment + self.probe

    @property
    def task_count(self) -> int:
        return len(self.all_tasks)
