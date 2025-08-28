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

from src.utils.loader import load_world_from_json
from src.utils.logger import get_logger
from src.world.settings import SETTINGS
from src.world.grid import to_cell, to_world
from src.world.pathfinding import GridSpec
from src.agent.npc_game import NPCAgent


class GameWindow(arcade.Window):
    def __init__(self, config_path: str | None = None) -> None:
        super().__init__(
            SETTINGS.WIDTH,
            SETTINGS.HEIGHT,
            "Autonomous LLM NPC — Visual",
            update_rate=1 / SETTINGS.FPS,
        )
        arcade.set_background_color(arcade.color.DARK_SPRING_GREEN)

        self.g = SETTINGS.GRID_SIZE
        self.log = get_logger("world.visual")  # logs/world/world.log

        # --- estado base
        self.show_path = True
        self.blocked_cells: set[tuple[int, int]] = set()
        self.blocked_sprites = arcade.SpriteList(use_spatial_hash=True)

        # Proveedor de GridSpec para el NPC (usa las celdas bloqueadas actuales)
        def grid_spec() -> GridSpec:
            w = SETTINGS.WIDTH // self.g
            h = SETTINGS.HEIGHT // self.g
            return GridSpec(w, h, blocked=set(self.blocked_cells))

        # --- objetos/NPCs
        from src.world.items import ObjectManager
        from src.world.areas.areas import AreaManager
        self.objects = ObjectManager()
        self.npcs: list[NPCAgent] = []

        if config_path:
            # factory de NPC para el loader (inyecta grid_spec, grid_size y speed)
            def make_npc(cfg: dict, om: ObjectManager, am: AreaManager) -> NPCAgent:
                speed = float(cfg.get("speed", 4.0))
                cell = tuple(cfg["cell"])
                npc = NPCAgent(
                    agent_id=str(cfg["id"]),
                    grid_size=self.g,
                    grid_spec_provider=grid_spec,
                    speed_cells_per_sec=speed,
                    initial_cell=tuple(cell),  # type: ignore
                    object_mgr=om,
                    area_mgr=am,
                )
                return npc

            bc, om, npcs, am = load_world_from_json(config_path, npc_factory=make_npc)
            self.blocked_cells = bc
            self.objects = om
            self.npcs = npcs  # puede haber varios
            self.area_mgr = am

            self.show_areas = True
        else:
            # fallback: tu setup anterior (1 NPC e items demo)
            from src.world.items import Gem, Shard, Relic
            self.objects.add(Gem((5, 5)), Shard((7, 8)), Relic((12, 6)))
            self.npcs = [NPCAgent("eldric", self.g, grid_spec, 6.0, (2, 3))]

        # reconstruye sprites de bloqueos en cualquier caso
        self._rebuild_blocked_sprites()

        # HUD
        self.hud = arcade.Text(
            "L: mover | R: parar | G: coger | H: soltar | P: path ON/OFF | B: bloque | C: limpiar | Q/ESC: salir",
            10, SETTINGS.HEIGHT - 24, arcade.color.WHITE, 14
        )

        self._mouse_cell: tuple[int, int] | None = None

    # ---------- helpers ----------
    def _rebuild_blocked_sprites(self) -> None:
        """Reconstruye la SpriteList a partir de blocked_cells."""
        self.blocked_sprites = arcade.SpriteList(use_spatial_hash=True)
        for (cx, cy) in self.blocked_cells:
            x, y = to_world((cx, cy), self.g)
            s = arcade.SpriteSolidColor(self.g, self.g, arcade.color.BLACK)  # ← negro
            s.center_x, s.center_y = x, y
            self.blocked_sprites.append(s)
    
    # ---------- loop ----------
    def on_draw(self) -> None:
        self.clear()
        self._draw_grid()
        self._draw_areas()
        self.blocked_sprites.draw()
        self._draw_objects()
        self._draw_path_debug()
        self._draw_npcs()
        self._draw_hud()

    def on_update(self, dt: float) -> None:
        for npc in self.npcs:
            npc.update(dt)

    # ---------- input ----------
    def on_mouse_motion(self, x: float, y: float, dx: float, dy: float) -> None:
        self._mouse_cell = to_cell((x, y), self.g)

    # y donde emitías órdenes, si por ahora solo “conduces” el primero:
    def on_mouse_press(self, x, y, button, modifiers):
        cell = to_cell((x, y), self.g)
        if not self.npcs:
            return
        npc = self.npcs[0]
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.log.info(f"cmd move_to cell={cell}")
            npc.move_to_cell(cell)
        elif button == arcade.MOUSE_BUTTON_RIGHT:
            self.log.info("cmd stop")
            npc.stop()

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol == arcade.key.R:
            # Demo simple: dos destinos
            self.npcs[0].move_to_cell((15, 10))
        elif symbol == arcade.key.B and self._mouse_cell is not None:
            # Toggle obstáculo en la celda del ratón
            c = self._mouse_cell
            if c in self.blocked_cells:
                self.blocked_cells.remove(c)
            else:
                # Evita bloquear justo donde está el NPC
                if c != self.npcs[0].current_cell():
                    self.blocked_cells.add(c)
            self._rebuild_blocked_sprites()
            self.log.info(f"toggle_block cell={c} now_blocked={c in self.blocked_cells}")
        elif symbol == arcade.key.C:
            self.blocked_cells.clear()
            self._rebuild_blocked_sprites()
            self.log.info("clear_blocks")
        elif symbol == arcade.key.ESCAPE or symbol == arcade.key.Q:
            self.log.info("[pingpong] Quit (ESC/Q pressed)")
            self.close()
        elif symbol == arcade.key.P:
            # Toggle mostrar camino
            self.show_path = not self.show_path
            state = "ON" if self.show_path else "OFF"
            self.log.info(f"[visual] Path visualization {state}")
        # en on_key_press de GameWindow
        elif symbol == arcade.key.G:
            cell = self.npcs[0].current_cell() if hasattr(self, "npcs") else self.npc.current_cell()
            npc = self.npcs[0] if hasattr(self, "npcs") else self.npc
            ok = self.objects.pick_up_near(npc.id, cell)
            self.log.info(f"pick_up_near at {cell}: {'OK' if ok else 'NOPE'}")

        elif symbol == arcade.key.H:
            cell = self.npcs[0].current_cell() if hasattr(self, "npcs") else self.npc.current_cell()
            npc = self.npcs[0] if hasattr(self, "npcs") else self.npc
            ok = self.objects.drop_held(npc.id, cell)
            self.log.info(f"drop_held at {cell}: {'OK' if ok else 'NOPE'}")
        elif symbol == arcade.key.A:
            self.show_areas = not self.show_areas

    # ---------- dibujo ----------
    def _draw_grid(self) -> None:
        color = arcade.color.DARK_SLATE_GRAY
        for x in range(0, SETTINGS.WIDTH + 1, self.g):
            arcade.draw_line(x, 0, x, SETTINGS.HEIGHT, color, 1)
        for y in range(0, SETTINGS.HEIGHT + 1, self.g):
            arcade.draw_line(0, y, SETTINGS.WIDTH, y, color, 1)

    def _draw_path_debug(self) -> None:
        if not self.show_path:
            return
        for npc in self.npcs:
            for cell in npc.get_path_cells():
                x, y = to_world(cell, self.g)
                arcade.draw_circle_outline(x, y, self.g * 0.3, arcade.color.YELLOW, 2)

    def _draw_hud(self) -> None:
        self.hud.draw()

    # -- donde uses self.npc, cambia a self.npcs[0] (si solo controlas uno)
    def _draw_npcs(self) -> None:
        # dibuja todos, por si hay varios
        radius = (self.g - 4) / 2
        for npc in self.npcs:
            x, y = npc.world_position()
            arcade.draw_circle_filled(x, y, radius, arcade.color.RED)

    def _draw_objects(self) -> None:
        self.objects.draw(self.g)

    def _draw_areas(self) -> None:
        if self.show_areas and getattr(self, "area_mgr", None):
            # una sola llamada, sin saber de estilos ni kinds
            from arcade import draw_text  # solo para evitar warnings del linter, no necesario
            from src.world.settings import SETTINGS
            self.area_mgr.draw_all(__import__("arcade"), SETTINGS.GRID_SIZE)
