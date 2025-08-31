from __future__ import annotations
from typing import Any, Dict, Tuple

from src.world.areas.areas import RectArea
from src.world.areas.areas_type import * # Import all subclass areas.
from src.world.grid import Cell

# ---------- helpers de parseo ----------
def _cell(obj: Any) -> Cell:
    # admite [x,y] o {"x":..,"y":..}
    if isinstance(obj, (tuple, list)) and len(obj) == 2:
        return (int(obj[0]), int(obj[1]))
    return (int(obj["x"]), int(obj["y"]))

def _rect(obj: Any) -> Tuple[int, int, int, int]:
    """
    Devuelve (left, bottom, right, top).
    Soporta:
      - [l,b,r,t] (r,t exclusivos)
      - {"l":..,"b":..,"r":..,"t":..}
      - {"left":..,"bottom":..,"right":..,"top":..}
      - [l,b,w,h]  -> convierte a (l, b, l+w, b+h)
    """
    if isinstance(obj, (tuple, list)) and len(obj) == 4:
        l, b, c, d = obj
        # heurística: si c/d son mayores que l/b, tratamos como r/t; si no, como w/h
        if c > l and d > b:
            return int(l), int(b), int(c), int(d)  # [l,b,r,t]
        else:
            # [l,b,w,h]
            return int(l), int(b), int(l) + int(c), int(b) + int(d)
    if isinstance(obj, dict):
        if all(k in obj for k in ("l", "b", "r", "t")):
            return int(obj["l"]), int(obj["b"]), int(obj["r"]), int(obj["t"])
        if all(k in obj for k in ("left", "bottom", "right", "top")):
            return int(obj["left"]), int(obj["bottom"]), int(obj["right"]), int(obj["top"])
    raise ValueError(f"Rect inválido: {obj!r}")

# mapping tipo->clase
AREA_TYPES = {
    "RectArea": RectArea,
    "BakeryArea": BakeryArea,
    "FarmArea": FarmArea,
    "BarArea": BarArea,
    # añade aquí otros tipos si los creas
}

def _build_area(area_spec: Dict[str, Any]):
    """
    Crea la instancia de área desde el dict del JSON.
    Espera claves:
      - id: str
      - type: str (coincide con las clases anteriores)
      - rects: lista de rects (ver _rect)
      - entrances: lista de celdas
      - anchor: celda (opcional; si no, primera celda del primer rect)
    """
    a_id = str(area_spec["id"])
    a_type = str(area_spec.get("type", "RectArea"))
    cls = AREA_TYPES.get(a_type, RectArea)

    rects = [_rect(r) for r in area_spec.get("rects", [])]
    if not rects:
        raise ValueError(f"Área '{a_id}' sin rectángulos")

    entrances = [_cell(c) for c in area_spec.get("entrances", [])]
    if not entrances:
        # opcional: intenta poner una entrada por defecto en el borde inferior izquierdo
        l, b, r, t = rects[0]
        entrances = [Cell(int(l), int(b + t) // 2)]

    if "anchor" in area_spec:
        anchor = _cell(area_spec["anchor"])
    else:
        # anchor por defecto: primera celda dentro del primer rect
        l, b, r, t = rects[0]
        anchor = Cell(int(l), int(b))

    # Las clases de área del repo aceptan: id, rects, entrances, anchor
    area = cls(area_id=a_id, rects=rects, entrances=entrances, anchor=anchor)
    return area