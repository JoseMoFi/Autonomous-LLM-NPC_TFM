# src/world/grid.py
from __future__ import annotations
from typing import Iterable, Iterator, List, Tuple

Cell = Tuple[int, int]
Point = Tuple[float, float]

def to_cell(pos_xy: Point, grid_size: int) -> Cell:
    """Pasa de coordenadas de mundo (px) a celda (enteros)."""
    x, y = pos_xy
    return int(x // grid_size), int(y // grid_size)

def to_world(cell: Cell, grid_size: int) -> Point:
    """Centro de celda → coordenadas de mundo (px)."""
    cx, cy = cell
    return (cx + 0.5) * grid_size, (cy + 0.5) * grid_size

def neighbors_4(cell: Cell) -> List[Cell]:
    """Vecinos en 4 direcciones (N,S,E,O)."""
    x, y = cell
    return [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]

def in_bounds(cell: Cell, width_cells: int, height_cells: int) -> bool:
    x, y = cell
    return 0 <= x < width_cells and 0 <= y < height_cells

def manhattan(a: Cell, b: Cell) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def iter_grid_cells(width_px: int, height_px: int, grid_size: int) -> Iterator[Cell]:
    """Itera por todas las celdas del mapa."""
    w = width_px // grid_size
    h = height_px // grid_size
    for cy in range(h):
        for cx in range(w):
            yield (cx, cy)
