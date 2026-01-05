from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Experiment:
    category: str
    name: str
    path: Path

    @property
    def display_name(self) -> str:
        return self.name.replace("_", " ")


def _category_from_path(root: Path, file_path: Path) -> str:
    relative_parent = file_path.parent.relative_to(root)
    if relative_parent.parts:
        return "/".join(relative_parent.parts)
    return "root"


def discover_experiments(root: Path, directories: list[str] | None = None) -> list[Experiment]:
    if directories is None:
        directories = ["standard", "OPA", "Bipolar"]

    experiments: list[Experiment] = []
    for directory in directories:
        folder = root / directory
        if not folder.exists():
            continue
        for file_path in sorted(folder.rglob("*.py")):
            if file_path.name == "__init__.py":
                continue
            category = _category_from_path(root, file_path)
            experiments.append(
                Experiment(
                    category=category,
                    name=file_path.stem,
                    path=file_path,
                )
            )

    return sorted(experiments, key=lambda item: (item.category, item.name))
