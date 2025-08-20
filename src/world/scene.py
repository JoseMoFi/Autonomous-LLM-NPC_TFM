# src/world/scene.py
"""
Capa visual mínima para el “mundo”:
- Dibuja una esplanada verde con grid.
- Un NPC controlado por NPCAgent (usa tu pathfinding A* 4-dir).
- Obstáculos opcionales alineados a celda (SpriteSolidColor).
Controles:
- Clic izquierdo: mover a la celda clicada.
- Clic derecho: parar.
- Tecla R: demo (ruta predefinida).
- Tecla B: alterna obstáculo en la celda del ratón.
- Tecla C: limpia obstáculos.
- ESC: salir.
"""

from __future__ import annotations
import arcade

from src.world.settings import SETTINGS
from src.world.grid import to_cell, to_world
from src.world.pathfinding import GridSpec
from src.agent.npc_game import NPCAgent
from src.utils.logger import get_logger


class GameWindow(arcade.Window):
    def __init__(self) -> None:
        super().__init__(
            SETTINGS.WIDTH,
            SETTINGS.HEIGHT,
            "Autonomous LLM NPC — Visual",
            update_rate=1 / SETTINGS.FPS,
        )
        arcade.set_background_color(arcade.color.DARK_SPRING_GREEN)

        self.g = SETTINGS.GRID_SIZE
        self.log = get_logger("world.visual")  # logs/world/world.log

        # Obstáculos en celdas (set de (cx, cy))
        self.blocked_cells: set[tuple[int, int]] = set()

        # Sprites para visualizar los obstáculos
        self.blocked_sprites = arcade.SpriteList(use_spatial_hash=True)
        self._rebuild_blocked_sprites()

        # Proveedor de GridSpec para el NPC (usa las celdas bloqueadas actuales)
        def grid_spec() -> GridSpec:
            w = SETTINGS.WIDTH // self.g
            h = SETTINGS.HEIGHT // self.g
            return GridSpec(w, h, blocked=set(self.blocked_cells))

        # NPC
        self.npc = NPCAgent(
            agent_id="eldric",
            grid_size=self.g,
            grid_spec_provider=grid_spec,
            speed_cells_per_sec=6.0,
            initial_cell=(2, 3),
        )

        # Sprite visual del NPC
        size = self.g - 4
        self.npc_sprite = arcade.SpriteSolidColor(size, size, arcade.color.RED)

        # Última celda del ratón (para B/C)
        self._mouse_cell: tuple[int, int] | None = None
        self.hud = arcade.Text(
            "L: mover | R: parar | R: demo | B: bloque | C: limpiar | ESC: salir",
            10, SETTINGS.HEIGHT - 24, arcade.color.WHITE, 14
        )

    # ---------- helpers ----------
    def _rebuild_blocked_sprites(self) -> None:
        """Reconstruye la SpriteList a partir de blocked_cells."""
        self.blocked_sprites = arcade.SpriteList(use_spatial_hash=True)
        for (cx, cy) in self.blocked_cells:
            x, y = to_world((cx, cy), self.g)
            s = arcade.SpriteSolidColor(self.g, self.g, arcade.color.DARK_BROWN)
            s.center_x, s.center_y = x, y
            self.blocked_sprites.append(s)

    # ---------- loop ----------
    def on_draw(self) -> None:
        self.clear()
        self._draw_grid()
        self.blocked_sprites.draw()
        self._draw_path_debug()
        self._draw_npc()
        self._draw_hud()

    def on_update(self, dt: float) -> None:
        self.npc.update(dt)

    # ---------- input ----------
    def on_mouse_motion(self, x: float, y: float, dx: float, dy: float) -> None:
        self._mouse_cell = to_cell((x, y), self.g)

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int) -> None:
        cell = to_cell((x, y), self.g)
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.log.info(f"cmd move_to cell={cell}")
            self.npc.move_to_cell(cell)
        elif button == arcade.MOUSE_BUTTON_RIGHT:
            self.log.info("cmd stop")
            self.npc.stop()

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol == arcade.key.R:
            # Demo simple: dos destinos
            self.npc.move_to_cell((15, 10))
        elif symbol == arcade.key.B and self._mouse_cell is not None:
            # Toggle obstáculo en la celda del ratón
            c = self._mouse_cell
            if c in self.blocked_cells:
                self.blocked_cells.remove(c)
            else:
                # Evita bloquear justo donde está el NPC
                if c != self.npc.current_cell():
                    self.blocked_cells.add(c)
            self._rebuild_blocked_sprites()
            self.log.info(f"toggle_block cell={c} now_blocked={c in self.blocked_cells}")
        elif symbol == arcade.key.C:
            self.blocked_cells.clear()
            self._rebuild_blocked_sprites()
            self.log.info("clear_blocks")
        elif symbol == arcade.key.ESCAPE:
            self.close()

    # ---------- dibujo ----------
    def _draw_grid(self) -> None:
        color = arcade.color.DARK_SLATE_GRAY
        for x in range(0, SETTINGS.WIDTH + 1, self.g):
            arcade.draw_line(x, 0, x, SETTINGS.HEIGHT, color, 1)
        for y in range(0, SETTINGS.HEIGHT + 1, self.g):
            arcade.draw_line(0, y, SETTINGS.WIDTH, y, color, 1)

    def _draw_path_debug(self) -> None:
        for cell in self.npc.get_path_cells():
            x, y = to_world(cell, self.g)
            arcade.draw_circle_outline(x, y, self.g * 0.3, arcade.color.YELLOW, 2)

    def _draw_npc(self) -> None:
    # Dibuja el NPC como un círculo sólido (versión-agnóstica)
        x, y = self.npc.world_position()
        radius = (self.g - 4) / 2
        arcade.draw_circle_filled(x, y, radius, arcade.color.RED)


    def _draw_hud(self) -> None:
        self.hud.draw()
