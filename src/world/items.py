from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Union
import itertools

import arcade

from src.world.grid import to_world
from src.utils.logger import get_logger

Cell = Tuple[int, int]
Color = Union[Tuple[int, int, int], Tuple[int, int, int, int]]  # RGB o RGBA

_id_counter = itertools.count(1)


@dataclass(init=True, repr=True, eq=False)
class WorldObject:
    """
    Objeto base cogible/soltable:
    - 'cell': celda donde está en el suelo (cuando no lo lleva nadie).
    - 'held_by': id del agente que lo lleva; si no es None, no se dibuja en el suelo.
    - 'color', 'name': apariencia mínima.
    """
    cell: Cell
    color: Color
    name: str = "object"
    id: str = field(default_factory=lambda: f"obj_{next(_id_counter)}")
    held_by: Optional[str] = None  # agent_id si lo lleva alguien

    # --- render mínimo (triángulo pequeño) ---
    def draw(self, grid_size: int) -> None:
        if self.held_by is not None:
            return  # en manos → no dibujar en el suelo
        x, y = to_world(self.cell, grid_size)
        r = grid_size * 0.30
        # Triángulo equilateral
        p0 = (x, y + r)
        p1 = (x - r * 0.8660254, y - r * 0.5)
        p2 = (x + r * 0.8660254, y - r * 0.5)
        arcade.draw_triangle_filled(p0[0], p0[1], p1[0], p1[1], p2[0], p2[1], self.color)

    # --- interacción ---
    def can_pick(self) -> bool:
        return self.held_by is None

    def pick_up(self, agent_id: str) -> bool:
        log = get_logger("world.objects")
        if not self.can_pick():
            log.info(f"pickup_failed id={self.id} held_by={self.held_by} agent={agent_id}")
            return False
        self.held_by = agent_id
        log.info(f"pickup_ok id={self.id} agent={agent_id}")
        return True

    def drop(self, cell: Cell) -> bool:
        log = get_logger("world.objects")
        if self.held_by is None:
            log.info(f"drop_ignored id={self.id} (already on ground) cell={cell}")
            return False
        self.held_by = None
        self.cell = cell
        log.info(f"drop_ok id={self.id} cell={cell}")
        return True


# --- Tipos concretos (3 por ahora) ---

class Gem(WorldObject):
    def __init__(self, cell: Cell):
        super().__init__(cell=cell, color=arcade.color.AQUAMARINE, name="gem")


class Shard(WorldObject):
    def __init__(self, cell: Cell):
        super().__init__(cell=cell, color=arcade.color.GOLD, name="shard")


class Relic(WorldObject):
    def __init__(self, cell: Cell):
        super().__init__(cell=cell, color=arcade.color.MAGENTA, name="relic")


# --- Gestor simple de objetos ---

class ObjectManager:
    def __init__(self) -> None:
        self._objects: List[WorldObject] = []

    def add(self, *objs: WorldObject) -> None:
        self._objects.extend(objs)

    def remove(self, obj: WorldObject) -> None:
        self._objects = [o for o in self._objects if o is not obj]

    def all(self) -> List[WorldObject]:
        return list(self._objects)

    def draw(self, grid_size: int) -> None:
        for o in self._objects:
            o.draw(grid_size)

    def objects_at_cell(self, cell: Cell) -> List[WorldObject]:
        return [o for o in self._objects if o.held_by is None and o.cell == cell]
