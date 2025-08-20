# src/world/movement.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

from .grid import Cell, to_world

@dataclass
class GridMover:
    """
    Mueve un actor por una ruta de celdas a velocidad fija (celdas/seg).
    4-direcciones (la ruta viene del pathfinder en 4-dir).
    """
    grid_size: int
    speed_cells_per_sec: float = 4.0
    path: List[Cell] = field(default_factory=list)
    _current_index: int = 0
    _pos_world: Tuple[float, float] = (0.0, 0.0)

    def set_cell_position(self, cell: Cell) -> None:
        self.path = []
        self._current_index = 0
        self._pos_world = to_world(cell, self.grid_size)

    def set_path(self, path: List[Cell]) -> None:
        """Asigna una ruta (incluye la celda actual y el goal)."""
        self.path = path[:] if path else []
        self._current_index = 0
        if self.path:
            self._pos_world = to_world(self.path[0], self.grid_size)

    def is_idle(self) -> bool:
        return not self.path or self._current_index >= len(self.path) - 1

    def world_position(self) -> Tuple[float, float]:
        return self._pos_world

    def current_cell(self) -> Optional[Cell]:
        if not self.path:
            return None
        return self.path[self._current_index]

    def target_cell(self) -> Optional[Cell]:
        if self.is_idle():
            return None
        return self.path[self._current_index + 1]

    def update(self, dt: float) -> None:
        """
        Avanza hacia la siguiente celda según velocidad.
        Hace snapping al centro de la celda objetivo cuando la alcanza.
        """
        if self.is_idle():
            return

        cx, cy = self.path[self._current_index]
        nx, ny = self.path[self._current_index + 1]

        x, y = self._pos_world
        tx = (nx + 0.5) * self.grid_size
        ty = (ny + 0.5) * self.grid_size

        # vector hacia target (solo 4-dir)
        dx = tx - x
        dy = ty - y

        # distancia a recorrer en este frame (en píxeles)
        pixels_per_sec = self.speed_cells_per_sec * self.grid_size
        step = pixels_per_sec * dt

        # mover clamped
        if abs(dx) + abs(dy) == 0:
            # ya está en el centro exacto
            self._current_index += 1
            return

        # Normaliza en 4-dir (dx o dy será 0)
        if abs(dx) > 0:
            move_x = max(-step, min(step, dx))
            x += move_x
        elif abs(dy) > 0:
            move_y = max(-step, min(step, dy))
            y += move_y

        self._pos_world = (x, y)

        # si hemos llegado (o pasado) al target, hacemos snap y avanzamos índice
        arrived_x = (dx == 0) or (dx > 0 and x >= tx) or (dx < 0 and x <= tx)
        arrived_y = (dy == 0) or (dy > 0 and y >= ty) or (dy < 0 and y <= ty)
        if arrived_x and arrived_y:
            self._pos_world = (tx, ty)
            self._current_index += 1
