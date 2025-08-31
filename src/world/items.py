from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Union
import itertools

import arcade

from src.world.grid import to_world, Cell
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

from src.world.items_type import *


# --- Gestor simple de objetos ---

from src.world.grid import neighbors_4  # ya lo tienes

class ItemErrorTypes:
    NO_ITEM: str = "ERROR_ITEM"
    BLOCKED_CELL: str = "BLOQUED_CELL"
    NO_MATCHING_TYPE: str = "NO_MATCHING_TYPE"
    OCCUPIED_CELL: str = "OCCUPIED_CELL"
    OBJ_NOT_FOUND: str = "OBJ_NOT_FOUND"
    QTY_GT1_SINGLE_CELL: str = "QTY_GT1_SINGLE_CELL"



class ObjectManager:
    def __init__(self) -> None:
        self._objects: dict[str, WorldObject] = {}
        # self._objects: list[WorldObject] = []
        self.obj_by_cell: dict[Cell, str] = {}  # celdas con objeto EN EL SUELO
        self._object_npc: dict[str, str] = {}
        self.world_blocked: set[Cell] = set()

    # ---- helpers ----
    def _is_occupied(self, cell: Cell) -> bool:
        return cell in self.obj_by_cell

    def set_world_blocked(self, world_blocked: set[Cell]) -> None:
        self.world_blocked |= world_blocked

    def add(self, *objs: WorldObject) -> None:
        for o in objs:
            self._objects[o.id] = o
            self._mark_add(o)

    def remove(self, obj: WorldObject) -> None:
        self._mark_remove(obj)
        self._objects = [o for o in self._objects if o is not obj]

    def all(self) -> list[WorldObject]:
        return list(self._objects)

    def draw(self, grid_size: int) -> None:
        for o in self._objects.values():
            o.draw(grid_size)

    def _mark_add(self, obj: WorldObject) -> None:
        if obj.held_by is None:
            if obj.cell in self.obj_by_cell:
                raise ValueError(f"Ya hay un objeto en {obj.cell}")
            self.obj_by_cell[obj.cell] = obj.id

    def _mark_remove(self, obj: WorldObject) -> None:
        if obj.held_by is None:
            self.obj_by_cell.remove(obj.cell)

    
    # ---- consultas ----
    def objects_at(self, cell: Cell) -> list[str]:
        oid = self.obj_by_cell.get(cell)
        return [oid] if oid else []

    def get_obj(self, obj_id: str) -> WorldObject | None:
        return self.objects.get(obj_id)

    # ---- validación ----
    def can_pick(self, *, cell: Cell, type_filter: str | None = None)-> Tuple[bool, str, str]: # Return: accessible, Error Type, object id.
        oid = self.obj_by_cell.get(cell)
        if not oid:
            return False, ItemErrorTypes.NO_ITEM, None
        if type_filter is None:
            return True, None, oid
        obj = self.objects.get(oid)
        return (True, None, oid) if (obj and obj.name == type_filter) else (False, ItemErrorTypes.NO_MATCHING_TYPE, None)

    def can_drop(self, *, cell: Cell) -> Tuple[bool, str]: # Return: accesible, Error type
        if cell in self.world_blocked:
            return False, ItemErrorTypes.BLOCKED_CELL
        if cell in self.obj_by_cell:
            return False, ItemErrorTypes.OCCUPIED_CELL
        return True, None

    # ---- commits (1 por celda) ----
    def commit_pick(self, *, agent_id: str, obj_id: str) -> Tuple[bool, str, str]: # Return: accessible, Error Type, object name.
        obj = self.objects.get(obj_id)
        if not obj:
            return False, ItemErrorTypes.OBJ_NOT_FOUND, None
        self.obj_by_cell.pop(obj.cell, None)
        self.objects.pop(obj_id, None)
        # emitir eventos / actualizar ledger si tienes
        return True, None, obj.name
    
    def commit_drop(self, *, agent_id: str, cell: Cell, item_type: str, qty: int = 1) -> Tuple[bool, str, List[str]]:
        if qty != 1:
            return False, ItemErrorTypes.QTY_GT1_SINGLE_CELL, []
        ok, reason = self.can_drop(cell=cell)
        if not ok:
            return False, reason, []
        obj = make_item(item_type, cell)
        obj_id = getattr(obj, "id", None) or f"obj_{len(self.objects)+1}"
        obj.id = obj_id
        self.objects[obj_id] = obj
        self.obj_by_cell[cell] = obj_id
        # emitir eventos / actualizar ledger si tienes
        return True, None, [obj_id]
    # ---- craft commit ----
    def commit_craft(self,item_type: str):
        pass

    # opcional: para el loader/editor
    def spawn(self, item_type: str, cell: Cell) -> str: # Return Object ID
        if self._is_occupied(cell):
            raise ValueError(f"{ItemErrorTypes.OCCUPIED_CELL} {cell}")
        obj = make_item(item_type, cell)
        obj_id = getattr(obj, "id", None) or f"obj_{len(self.objects)+1}"
        obj.id = obj_id
        self.objects[obj_id] = obj
        self.obj_by_cell[cell] = obj_id
        return obj_id
    # # --- internos ---
    # def _rebuild_occupancy(self) -> None:
    #     self._occupied = {o.cell for o in self._objects if o.held_by is None}

    # def _mark_add(self, obj: WorldObject) -> None:
    #     if obj.held_by is None:
    #         if obj.cell in self._occupied:
    #             raise ValueError(f"Ya hay un objeto en {obj.cell}")
    #         self._occupied.add(obj.cell)

    # def _mark_remove(self, obj: WorldObject) -> None:
    #     if obj.held_by is None:
    #         self._occupied.discard(obj.cell)

    # # --- API ---
    # def add(self, *objs: WorldObject) -> None:
    #     for o in objs:
    #         self._objects.append(o)
    #         self._mark_add(o)

    # def remove(self, obj: WorldObject) -> None:
    #     self._mark_remove(obj)
    #     self._objects = [o for o in self._objects if o is not obj]

    # def all(self) -> list[WorldObject]:
    #     return list(self._objects)

    # def draw(self, grid_size: int) -> None:
    #     for o in self._objects:
    #         o.draw(grid_size)

    # def objects_at_cell(self, cell: Cell) -> list[WorldObject]:
    #     return [o for o in self._objects if o.held_by is None and o.cell == cell]

    # def is_free(self, cell: Cell) -> bool:
    #     return cell not in self._occupied

    # # --- reglas pedidas ---
    # def pickable_near(self, agent_cell: Cell) -> list[WorldObject]:
    #     """Objetos cogibles en misma celda o adyacentes 4-dir."""
    #     cands: list[WorldObject] = []
    #     scan = [agent_cell, *neighbors_4(agent_cell)]
    #     for c in scan:
    #         for o in self._objects:
    #             if o.held_by is None and o.cell == c:
    #                 cands.append(o)
    #     return cands

    # def pick_up_near(self, agent_id: str, agent_cell: Cell) -> bool:
    #     """Intenta coger el primero disponible en radio 4-dir (incluida la celda)."""
    #     for o in self.pickable_near(agent_cell):
    #         if o.pick_up(agent_id):
    #             # sale del suelo -> libera su celda
    #             self._occupied.discard(o.cell)
    #             return True
    #     return False

    # def drop_held(self, agent_id: str, cell: Cell) -> bool:
    #     """
    #     Suelta la PRIMERA pieza que lleve el agente en 'cell' si esa celda está libre.
    #     """
    #     if not self.is_free(cell):
    #         # ya hay pieza en esa celda
    #         get_logger("world.objects").info(f"drop_blocked agent={agent_id} cell={cell}")
    #         return False
    #     for o in self._objects:
    #         if o.held_by == agent_id:
    #             o.held_by = None
    #             o.cell = cell
    #             self._occupied.add(cell)
    #             get_logger("world.objects").info(f"drop_ok id={o.id} agent={agent_id} cell={cell}")
    #             return True
    #     return False

    # # utilidad por si tocas estados a mano
    # def sync(self) -> None:
    #     self._rebuild_occupancy()
