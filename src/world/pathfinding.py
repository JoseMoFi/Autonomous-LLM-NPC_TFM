# src/world/pathfinding.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple
import heapq

from .grid import Cell, neighbors_4, in_bounds, manhattan

@dataclass(frozen=True)
class GridSpec:
    width_cells: int
    height_cells: int
    blocked: Set[Cell]  # celdas no transitables

def reconstruct_path(came_from: Dict[Cell, Cell], start: Cell, goal: Cell) -> List[Cell]:
    if goal not in came_from and goal != start:
        return []
    cur = goal
    out = [cur]
    while cur != start:
        cur = came_from[cur]
        out.append(cur)
    out.reverse()
    return out

def astar(start: Cell, goal: Cell, grid: GridSpec) -> List[Cell]:
    """
    A* clásico sobre grid 4-dir. Coste uniforme (1 por paso).
    Devuelve la secuencia de celdas (incluye start y goal). Si no hay ruta → [].
    """
    if start == goal:
        return [start]

    if not in_bounds(start, grid.width_cells, grid.height_cells):
        return []
    if not in_bounds(goal, grid.width_cells, grid.height_cells):
        return []
    if start in grid.blocked or goal in grid.blocked:
        return []

    open_heap: List[Tuple[int, Cell]] = []
    heapq.heappush(open_heap, (0, start))
    came_from: Dict[Cell, Cell] = {}
    g_score: Dict[Cell, int] = {start: 0}

    closed: Set[Cell] = set()

    while open_heap:
        _, current = heapq.heappop(open_heap)
        if current == goal:
            return reconstruct_path(came_from, start, goal)

        if current in closed:
            continue
        closed.add(current)

        for nb in neighbors_4(current):
            if not in_bounds(nb, grid.width_cells, grid.height_cells):
                continue
            if nb in grid.blocked:
                continue

            tentative = g_score[current] + 1  # coste uniforme
            if tentative < g_score.get(nb, 1_000_000_000):
                came_from[nb] = current
                g_score[nb] = tentative
                f = tentative + manhattan(nb, goal)
                heapq.heappush(open_heap, (f, nb))

    return []  # no ruta
