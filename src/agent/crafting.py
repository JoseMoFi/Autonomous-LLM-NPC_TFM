from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Tuple

from world.recipe import RecipeRegistry, Recipe
from agent.inventory import Inventory

class CraftError(Enum):
    UNKNOWN_RECIPE = auto()
    NOT_KNOWN = auto()
    WRONG_STATION = auto()
    MISSING_INPUTS = auto()
    ALREADY_BUSY = auto()
    INVALID_QTY = auto()

@dataclass
class CraftTask:
    recipe: Recipe
    qty_total: int
    qty_remaining: int
    time_left_unit: float  # tiempo restante para la unidad actual

class Crafter:
    """
    Componente de crafteo que vive dentro del NPC.
    Gestiona validaciones, consumo/producción e integración temporal.
    """
    def __init__(self, owner: "NPCAgent", registry: RecipeRegistry, known_recipes: set[str], inventory: Inventory):
        self.owner = owner
        self.registry = registry
        self.known_recipes = known_recipes
        self.inventory = inventory
        self._task: Optional[CraftTask] = None

    # --- API ---
    def start(self, recipe_name: str, qty: int) -> Tuple[bool, Optional[CraftError], Optional[str]]:
        if self._task is not None:
            return False, CraftError.ALREADY_BUSY, "Already crafting."
        if qty <= 0:
            return False, CraftError.INVALID_QTY, "Quantity must be > 0."

        recipe = self.registry.get(recipe_name)
        if recipe is None:
            return False, CraftError.UNKNOWN_RECIPE, f"Recipe '{recipe_name}' not found."
        if recipe_name not in self.known_recipes:
            return False, CraftError.NOT_KNOWN, f"NPC does not know '{recipe_name}'."

        # estación requerida
        if recipe.station is not None:
            if self.owner.current_area_name != recipe.station:
                return False, CraftError.WRONG_STATION, f"Must be inside '{recipe.station}'."

        # consumo estricto (toda la qty al inicio)
        total_inputs = {k: v * qty for k, v in recipe.inputs.items()}
        if not self.inventory.remove(total_inputs):
            return False, CraftError.MISSING_INPUTS, "Not enough inputs."

        self._task = CraftTask(recipe=recipe, qty_total=qty, qty_remaining=qty, time_left_unit=recipe.time_per_unit)
        return True, None, None

    def update(self, dt: float) -> None:
        t = self._task
        if t is None:
            return
        # cancelar si sale de la estación requerida
        if t.recipe.station is not None and self.owner.current_area_name != t.recipe.station:
            self._task = None
            return

        remaining = float(dt)
        while t is not None and remaining > 0 and t.qty_remaining > 0:
            if remaining >= t.time_left_unit:
                remaining -= t.time_left_unit
                # produce 1 unidad
                self.owner.inventory.add(t.recipe.outputs)
                t.qty_remaining -= 1
                t.time_left_unit = t.recipe.time_per_unit
            else:
                t.time_left_unit -= remaining
                remaining = 0.0

            if t.qty_remaining == 0:
                self._task = None
                break
            t = self._task

    def cancel(self) -> None:
        self._task = None  # política simple: no devuelve insumos

    def is_active(self) -> bool:
        return self._task is not None

    def progress(self) -> Optional[dict]:
        if self._task is None:
            return None
        done = self._task.qty_total - self._task.qty_remaining
        return {
            "recipe": self._task.recipe.name,
            "done": float(done),
            "total": float(self._task.qty_total),
            "unit_time_left": float(self._task.time_left_unit),
        }
