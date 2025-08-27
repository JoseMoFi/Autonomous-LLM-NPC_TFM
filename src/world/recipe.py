from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional
import yaml, os

@dataclass(frozen=True)
class Recipe:
    name: str
    inputs: Dict[str, int]
    outputs: Dict[str, int]
    time_per_unit: float
    station: Optional[str] = None

class RecipeRegistry:
    def __init__(self, recipes: Dict[str, Recipe]):
        self._recipes = recipes

    @classmethod
    def from_yaml(cls, path: str) -> "RecipeRegistry":
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        recs: Dict[str, Recipe] = {}
        for name, spec in raw.items():
            recs[name] = Recipe(
                name=name,
                inputs={k:int(v) for k,v in (spec.get("inputs") or {}).items()},
                outputs={k:int(v) for k,v in (spec.get("outputs") or {}).items()},
                time_per_unit=float(spec["time_per_unit"]),
                station=spec.get("station"),
            )
        return cls(recs)

    def get(self, name: str) -> Optional[Recipe]:
        return self._recipes.get(name)
