# src/world/areas.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional, Iterable, Dict, Type

Cell = Tuple[int, int]
Rect = Tuple[int, int, int, int]  # (x1, y1, x2, y2) inclusivo

# ----------------------------
# Estilo y helpers de dibujo
# ----------------------------

@dataclass(frozen=True)
class AreaStyle:
    fill_rgb: Tuple[int, int, int]      # sin alpha
    border_rgb: Tuple[int, int, int]
    fill_alpha: int = 50                # 0..255
    border_alpha: int = 180             # 0..255
    border_px: int = 2
    label_color: Tuple[int, int, int] = (0, 0, 0)
    label_px: int = 12

def _cell_rect_to_px(rect: Rect, cell_px: int) -> Tuple[float, float, float, float]:
    x1, y1, x2, y2 = rect
    left   = x1 * cell_px
    right  = (x2 + 1) * cell_px
    bottom = y1 * cell_px
    top    = (y2 + 1) * cell_px
    return left, right, bottom, top

def _rgba(rgb: Tuple[int, int, int], a: int) -> Tuple[int, int, int, int]:
    r, g, b = rgb
    return (r, g, b, a)

# ---------------------------------
# Clases de área (rectangulares)
# ---------------------------------

class RectArea:
    """
    Base rectangular (o unión de rectángulos) sobre grid.
    NO conoce Arcade: recibe las funciones/objeto 'arcade' desde fuera.
    Subclases definen KIND y STYLE.
    """
    KIND: str = "area"
    STYLE: AreaStyle = AreaStyle((180, 180, 180), (120, 120, 120))

    __slots__ = ("id", "kind", "rects", "entrances", "anchor")

    def __init__(
        self,
        area_id: str,
        rects: List[Rect],
        entrances: Optional[List[Cell]] = None,
        anchor: Optional[Cell] = None,
    ) -> None:
        self.id = area_id
        self.kind = type(self).KIND
        self.rects = rects
        self.entrances = set(entrances or [])
        self.anchor = anchor
        self._label_cache = {}  # dict[int cell_px -> arcade.Text]
    def _label_center_px(self, cell_px: int):
        ax, ay = self.anchor if self.anchor else self._bbox_center_cell()
        return (ax + 0.5) * cell_px, (ay + 0.5) * cell_px

    def _get_label(self, arcade_mod, cell_px: int):
        st = type(self).STYLE
        key = cell_px
        if key not in self._label_cache:
            cx, cy = self._label_center_px(cell_px)
            text = f"{self.kind}:{self.id}"
            self._label_cache[key] = arcade_mod.Text(
                text, cx, cy, st.label_color, st.label_px,
                anchor_x="center", anchor_y="center"
            )
        return self._label_cache[key]

    # --- lógica geométrica ---

    def contains(self, cell: Cell) -> bool:
        x, y = cell
        for x1, y1, x2, y2 in self.rects:
            if x1 <= x <= x2 and y1 <= y <= y2:
                return True
        return False

    def perimeter_cells(self) -> Iterable[Cell]:
        seen = set()
        for x1, y1, x2, y2 in self.rects:
            for x in range(x1, x2 + 1):
                for y in (y1, y2):
                    c = (x, y)
                    if c not in seen:
                        seen.add(c); yield c
            for y in range(y1 + 1, y2):
                for x in (x1, x2):
                    c = (x, y)
                    if c not in seen:
                        seen.add(c); yield c

    def bbox(self) -> Rect:
        xs1, ys1, xs2, ys2 = [], [], [], []
        for x1, y1, x2, y2 in self.rects:
            xs1.append(x1); ys1.append(y1); xs2.append(x2); ys2.append(y2)
        return (min(xs1), min(ys1), max(xs2), max(ys2))

    # --- dibujo (sin contaminar scene) ---

    def draw(self, arcade, cell_px: int) -> None:
        """
        Dibuja el área (relleno + borde + etiqueta). 'arcade' es el módulo inyectado.
        """
        st = type(self).STYLE
        # Relleno
        for rect in self.rects:
            l, r, b, t = _cell_rect_to_px(rect, cell_px)
            arcade.draw_lrbt_rectangle_filled(l, r, b, t, _rgba(st.fill_rgb, st.fill_alpha))
        # Borde
        for rect in self.rects:
            l, r, b, t = _cell_rect_to_px(rect, cell_px)
            arcade.draw_lrbt_rectangle_outline(l, r, b, t, _rgba(st.border_rgb, st.border_alpha), st.border_px)
        # Etiqueta (en anchor si existe; si no, en el centro de la bbox)
        # Etiqueta cacheada
        self._get_label(arcade, cell_px).draw()

    def _bbox_center_cell(self) -> Cell:
        x1, y1, x2, y2 = self.bbox()
        return ((x1 + x2) // 2, (y1 + y2) // 2)

# -----------------------
# Subclases tipadas
# -----------------------

class BakeryArea(RectArea):
    KIND = "bakery"
    STYLE = AreaStyle(
        fill_rgb=(255, 165, 0),      # naranja suave
        border_rgb=(200, 120, 0),
        fill_alpha=50,
        border_alpha=200,
        border_px=2,
        label_color=(0, 0, 0),
        label_px=12,
    )

class BarArea(RectArea):
    KIND = "bar"
    STYLE = AreaStyle(
        fill_rgb=(90, 200, 255),     # azul claro
        border_rgb=(20, 120, 200),
        fill_alpha=50,
        border_alpha=200,
        border_px=2,
        label_color=(0, 0, 0),
        label_px=12,
    )

class FarmArea(RectArea):  # cultivo
    KIND = "farm"
    STYLE = AreaStyle(
        fill_rgb=(140, 220, 120),    # verde suave
        border_rgb=(60, 140, 60),
        fill_alpha=50,
        border_alpha=200,
        border_px=2,
        label_color=(0, 0, 0),
        label_px=12,
    )

# ---------------------------------
# Factory y Manager
# ---------------------------------

_KIND_TO_CLASS: Dict[str, Type[RectArea]] = {
    BakeryArea.KIND: BakeryArea,
    BarArea.KIND:    BarArea,
    FarmArea.KIND:   FarmArea,
}

class AreaFactory:
    @staticmethod
    def from_json(entry: dict) -> RectArea:
        """
        Crea la subclase correcta según entry['kind'].
        entry:
          { id, kind in {'bakery','bar','farm'}, rects, entrances?, anchor? }
        """
        area_id = entry["id"]
        kind = entry["kind"].lower()
        rects = [tuple(r) for r in entry["rects"]]
        entrances = [tuple(c) for c in entry.get("entrances", [])]
        anchor = tuple(entry["anchor"]) if entry.get("anchor") else None

        cls = _KIND_TO_CLASS.get(kind, RectArea)  # fallback a genérico
        return cls(area_id=area_id, rects=rects, entrances=entrances, anchor=anchor)

class AreaManager:
    def __init__(self, areas: List[RectArea]) -> None:
        self._areas: Dict[str, RectArea] = {a.id: a for a in areas}
        self._by_kind: Dict[str, List[str]] = {}
        for a in areas:
            self._by_kind.setdefault(a.kind, []).append(a.id)

    # queries
    def area(self, area_id: str) -> RectArea:
        return self._areas[area_id]

    def try_area(self, area_id: str) -> Optional[RectArea]:
        return self._areas.get(area_id)

    def areas_for_cell(self, cell: Cell) -> List[str]:
        return [a.id for a in self._areas.values() if a.contains(cell)]

    def by_kind(self, kind: str) -> List[str]:
        return self._by_kind.get(kind, [])

    def all_ids(self) -> List[str]:
        return list(self._areas.keys())

    def __len__(self) -> int:
        return len(self._areas)

    # dibujo (centralizado aquí para no ensuciar scene)
    def draw_all(self, arcade, cell_px: int) -> None:
        for a in self._areas.values():
            a.draw(arcade, cell_px)
