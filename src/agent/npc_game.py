# src/agent/npc.py
from __future__ import annotations
from typing import Callable, Optional

from src.world.grid import to_cell, Cell
from src.world.pathfinding import GridSpec, astar
from src.world.movement import GridMover
from src.world.recipe import RecipeRegistry
from src.world.items import ObjectManager
from src.world.areas.areas import AreaManager
from src.utils.logger import get_logger
from src.agent.inventory import Inventory
from src.agent.crafting import Crafter


class NPCAgent:
    """
    NPC minimalista:
    - Mantiene su posición con GridMover (4-direcciones, velocidad fija)
    - Expone órdenes: spawn_at, move_to_cell/point, stop, is_idle
    - Calcula path con A* usando un proveedor de GridSpec (el mundo)
    - Loggea en logs/agents/<agent_id>.log
    """
    def __init__(
        self,
        agent_id: str,
        grid_size: int,
        grid_spec_provider: Callable[[], GridSpec],
        object_mgr: ObjectManager,
        area_mgr: AreaManager,
        speed_cells_per_sec: float = 4.0,
        initial_cell: Optional[Cell] = (1, 1),
        recipe_registry: RecipeRegistry | None = None,
        **kwargs
    ) -> None:
        self.id = agent_id
        self.grid_size = grid_size
        self._grid_spec_provider = grid_spec_provider
        self.mover = GridMover(grid_size=grid_size, speed_cells_per_sec=speed_cells_per_sec)

        self.object_mgr = object_mgr
        self.area_mgr = area_mgr

        self._current_area_name: str | None = None

        self.log_file = f"logs/agents/{agent_id}.log"
        self.log = get_logger(f"agent.{agent_id}", self.log_file)

        if initial_cell is not None:
            self.spawn_at(initial_cell)
        
        self.inventory = Inventory()
        self.known_recipes: set[str] = set()
        if recipe_registry is None:
            from pathlib import Path
            recipe_registry = RecipeRegistry.from_yaml(str(Path("data/recipes/recipes.yaml")))
        # crafter
        self.crafter = Crafter(self, recipe_registry, self.known_recipes, self.inventory)

    # ----- estado
    def world_position(self) -> tuple[float, float]:
        return self.mover.world_position()

    def current_cell(self) -> Cell:
        x, y = self.world_position()
        return to_cell((x, y), self.grid_size)

    def is_idle(self) -> bool:
        return self.mover.is_idle()

    def get_path_cells(self) -> list[Cell]:
        return list(self.mover.path)

    # ----- órdenes (con logs)
    def spawn_at(self, cell: Cell) -> None:
        self.mover.set_cell_position(cell)
        self._last_cell = cell
        self.log.info(f"action=spawn_at cell={cell}")

    def move_to_cell(self, cell: Cell) -> bool:
        start = self.current_cell()
        self.log.info(f"action=move_request start={start} goal={cell}")
        grid = self._grid_spec_provider()
        path = astar(start, cell, grid)
        if not path:
            self.log.warning(f"action=no_path start={start} goal={cell}")
            self.mover.set_path([])
            return False
        self.mover.set_path(path)
        self.log.info(f"action=path_set start={start} goal={cell} steps={len(path)}")
        return True

    def move_to_point(self, x: float, y: float) -> bool:
        return self.move_to_cell(to_cell((x, y), self.grid_size))

    def stop(self) -> None:
        self.mover.set_path([])
        self.log.info("action=stop")

    def craft_object(self, object):
        # TODO: hacer la llamada al crafter para hacer X objeto
        pass

    def update(self, dt: float) -> None:
        prev_cell = self.current_cell()
        prev_target = self.mover.target_cell()
        self.mover.update(dt)
        new_cell = self.current_cell()
        new_target = self.mover.target_cell()

        if prev_cell != new_cell:
            self.set_current_area_name(new_cell)

        # log cuando avanza de celda
        if new_cell != prev_cell:
            self.log.info(f"action=step cell_from={prev_cell} cell_to={new_cell}")
            self._last_cell = new_cell

        # log de llegada (cuando ya no hay target)
        if prev_target is not None and new_target is None and self.is_idle():
            self.log.info(f"action=arrived cell={new_cell}")
        
        self.crafter.update(dt)

    def set_current_area_name(self, cell: Cell) -> None:
        a = self.area_mgr.area_at(cell)
        self._current_area_name = type(a).__name__ if a else "BaseArea"
    
    # util para el crafter
    @property
    def current_area_name(self) -> str | None:
        return self._current_area_name
