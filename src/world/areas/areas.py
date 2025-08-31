# src/world/areas.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional, Iterable, Dict, Type, Set

from src.world.settings import SETTINGS

Cell = Tuple[int, int]
Rect = Tuple[int, int, int, int]  # (x1, y1, x2, y2) inclusivo

CellKey = Tuple[int, int]

def _cell_key(cell) -> CellKey:
    """Acepta tuplas/listas (cx,cy) o objetos con .x/.y."""
    try:
        return int(cell[0]), int(cell[1])
    except Exception:
        return int(getattr(cell, "x")), int(getattr(cell, "y"))


def _rect_bounds(rect) -> Tuple[int, int, int, int]:
    """
    Extrae (l,b,r,t). Asume rects 'exclusivos' en r,t (range(l,r), range(b,t)).
    Si tus rects son inclusivos, cambia a r+=1, t+=1 al indexar.
    """
    if isinstance(rect, (tuple, list)) and len(rect) == 4:
        l, b, r, t = rect
        return int(l), int(b), int(r), int(t)
    # soporte de dataclass/objeto: left/right/bottom/top o l/r/b/t
    names = ("left", "bottom", "right", "top")
    if all(hasattr(rect, n) for n in names):
        return int(rect.left), int(rect.bottom), int(rect.right), int(rect.top)
    alt = ("l", "b", "r", "t")
    if all(hasattr(rect, n) for n in alt):
        return int(rect.l), int(rect.b), int(rect.r), int(rect.t)
    raise TypeError(f"Rect desconocido: {rect!r}")

CELL_SIZE = SETTINGS.GRID_SIZE

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

def _tint(rgb: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
    """factor>1.0 aclara, 0<factor<1.0 oscurece."""
    r, g, b = rgb
    return (min(int(r*factor), 255), min(int(g*factor), 255), min(int(b*factor), 255))

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

    __slots__ = ("id", "kind", "rects", "entrances", "anchor", "_label_cache")

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

    def perimeter_block_cells(self) -> Iterable[Cell]:
        """Perímetro no transitable = perímetro - entradas."""
        entrances = set(self.entrances)
        for c in self.perimeter_cells():
            if c not in entrances:
                yield c

    def bbox(self) -> Rect:
        xs1, ys1, xs2, ys2 = [], [], [], []
        for x1, y1, x2, y2 in self.rects:
            xs1.append(x1); ys1.append(y1); xs2.append(x2); ys2.append(y2)
        return (min(xs1), min(ys1), max(xs2), max(ys2))
    
    def _bbox_center_cell(self) -> Cell:
        """
            Celda central del bbox. Para r,t EXCLUSIVOS, la última celda válida es r-1,t-1.
            Usamos floor para caer en una celda válida.
        """
        # Si tienes anchor definido y quieres priorizarlo para etiquetar:
        if getattr(self, "anchor", None):
            return self.anchor  # type: ignore[return-value]

        l, b, r, t = self.bbox()
        cx = (l + (r - 1)) // 2   # centro discreto en X
        cy = (b + (t - 1)) // 2   # centro discreto en Y
        return (int(cx), int(cy))

    # --- dibujo (sin contaminar scene) ---

    def draw(self, arcade, cell_px: int) -> None:
        st = type(self).STYLE
        # Relleno
        for rect in self.rects:
            l, r, b, t = _cell_rect_to_px(rect, cell_px)
            arcade.draw_lrbt_rectangle_filled(l, r, b, t, _rgba(st.fill_rgb, st.fill_alpha))
        # Borde
        for rect in self.rects:
            l, r, b, t = _cell_rect_to_px(rect, cell_px)
            arcade.draw_lrbt_rectangle_outline(l, r, b, t, _rgba(st.border_rgb, st.border_alpha), st.border_px)
        # Entradas: resáltalas con un tono más claro del fill
        entrance_color = _tint(st.fill_rgb, 1.3)  # 30% más claro
        for (cx, cy) in self.entrances:
            l = cx * cell_px
            r = (cx + 1) * cell_px
            b = cy * cell_px
            t = (cy + 1) * cell_px
            arcade.draw_lrbt_rectangle_filled(l, r, b, t, _rgba(entrance_color, max(80, st.fill_alpha)))
            arcade.draw_lrbt_rectangle_outline(l, r, b, t, _rgba(st.border_rgb, st.border_alpha), 2)
        # Etiqueta (cacheada)
        self._get_label(arcade, cell_px).draw()


# ---------------------------------
# Factory y Manager
# ---------------------------------
from src.world.areas.areas_type import *
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
    """
    Gestiona áreas y ofrece consultas O(1) por celda.
    - _areas: dict id->area (mantiene tu API draw_all/perimeter_blocked_cells)
    - _cell_to_areas: (cx,cy) -> [area_id,...] (última insertada tiene prioridad)
    - _perimeter_cache: set[Cell] (se invalida al mutar)
    """

    def __init__(self, areas: Optional[Dict[str, "BaseArea"]] = None):
        self._areas: Dict[str, "BaseArea"] = dict(areas or {})
        self._cell_to_areas: Dict[CellKey, List[str]] = {}
        self._perimeter_cache: Optional[Set["Cell"]] = None
        self._build_index()

    # ---------- índice interno ----------
    def _build_index(self) -> None:
        self._cell_to_areas.clear()
        for a in self._areas.values():
            self._index_area(a)

    def _index_area(self, area: "BaseArea") -> None:
        for rect in getattr(area, "rects", []):
            l, b, r, t = _rect_bounds(rect)
            # Si tus rectángulos son inclusivos en r,t cambia: range(l, r+1) / range(b, t+1)
            for cx in range(l, r):
                for cy in range(b, t):
                    self._cell_to_areas.setdefault((cx, cy), []).append(area.id)

    # ---------- mutación ----------
    def add(self, area: "BaseArea") -> None:
        assert area.id not in self._areas, f"Área duplicada: {area.id}"
        self._areas[area.id] = area
        self._index_area(area)
        self._perimeter_cache = None  # invalida cache

    def remove(self, area_id: str) -> None:
        if self._areas.pop(area_id, None) is None:
            return
        # Reconstrucción completa para mantener el índice correcto y simple
        self._build_index()
        self._perimeter_cache = None

    def rebuild_index(self) -> None:
        """Llama si cambias 'rects' de alguna área en caliente."""
        self._build_index()
        self._perimeter_cache = None

    # ---------- consultas O(1) ----------
    def areas_for_cell(self, cell) -> List[str]:
        """Devuelve ids de áreas que contienen la celda (puede haber solapes)."""
        return list(self._cell_to_areas.get(_cell_key(cell), []))

    def area_at(self, cell) -> Optional["BaseArea"]:
        """Área 'principal' en la celda; política: la última insertada gana en solape."""
        ids = self._cell_to_areas.get(_cell_key(cell))
        if not ids:
            return None
        return self._areas[ids[-1]]

    def area(self, area_id: str) -> Optional["BaseArea"]:
        return self._areas.get(area_id)

    def all(self) -> List["BaseArea"]:
        return list(self._areas.values())

    # Compat si en algún sitio usas .areas()
    def areas(self) -> Iterable["BaseArea"]:
        return self._areas.values()

    # ---------- utilidades existentes ----------
    def draw_all(self, arcade, cell_px: int) -> None:
        for a in self._areas.values():
            a.draw(arcade, cell_px)

    def perimeter_blocked_cells(self) -> Set["Cell"]:
        if self._perimeter_cache is None:
            out: Set["Cell"] = set()
            for a in self._areas.values():
                out.update(a.perimeter_block_cells())
            self._perimeter_cache = out
        # devuelve una copia para evitar mutaciones externas del cache
        return set(self._perimeter_cache)
    
    def __len__(self):
        return len(self.all())
