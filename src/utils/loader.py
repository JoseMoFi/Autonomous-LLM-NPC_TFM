# src/world/loader.py
from __future__ import annotations
from pathlib import Path
from typing import Callable, Iterable, Any

import json
from typing import Any, Dict, List, Tuple

from src.utils.logger import get_logger
from src.world.items import ObjectManager, WorldObject
from src.world.items_type import *
from src.world.areas.areas import AreaFactory, AreaManager
from src.world.areas.areas_helper import _build_area

log = get_logger("world.loader")

# ---- helpers de validación/normalización ----

def _as_cell(value: Any) -> tuple[int, int]:
    if (isinstance(value, (list, tuple)) and len(value) == 2
            and all(isinstance(v, (int, float)) for v in value)):
        # admitimos float pero truncamos a int por seguridad
        return int(value[0]), int(value[1])
    raise ValueError(f"Celda inválida: {value!r}")

# def _item_from_cfg(cfg: dict) -> WorldObject:
#     t = str(cfg.get("type", "")).lower().strip()
#     cell = _as_cell(cfg.get("cell"))
#     if t == "gem":
#         return Gem(cell)
#     if t == "shard":
#         return Shard(cell)
#     if t == "relic":
#         return Relic(cell)
#     raise ValueError(f"Tipo de item desconocido: {t!r}")

# ---- Area Loader ----

def load_areas(area_specs: List[Dict[str, Any]]) -> AreaManager:
    """
    Crea un AreaManager con índice O(1) a partir de la lista de specs del JSON.
    """
    areas_dict: Dict[str, Any] = {}
    for spec in area_specs or []:
        area = _build_area(spec)
        if area.id in areas_dict:
            raise ValueError(f"Área duplicada en JSON: {area.id}")
        areas_dict[area.id] = area

    am = AreaManager(areas_dict)  # dict id->area
    return am

# ---- API pública ----

def load_world_from_json(
    json_path: str | Path,
    npc_factory: Callable[[dict], Any],
):
    """
    Carga bloqueos, items y NPCs desde JSON.
    - npc_factory: callable que recibe el dict de un NPC del JSON y devuelve una instancia (p.ej. NPCAgent).
      Esto permite inyectar grid_spec_provider, grid_size, etc. desde tu escena.
    Devuelve: (blocked_cells: set[(int,int)], object_manager: ObjectManager, npcs: list[Any])
    """
    p = Path(json_path)
    data = json.loads(p.read_text(encoding="utf-8"))

    # 1) bloqueos
    blocked_cells = set()
    for c in data.get("blocked", []):
        blocked_cells.add(_as_cell(c))

    # 2) items
    object_mgr = ObjectManager()

    items_cfg = data.get("items", []) or []
    for it in items_cfg:
        t = str(it["type"]).lower()
        cx, cy = it["cell"]  # asegúrate de que viene como [x,y]
        cell = (int(cx), int(cy))  # tupla nativa, NO Cell(...)
        obj = make_item(t, cell)
        object_mgr.add(obj)
    
    # 3) Areas
    areas_cfg = data.get("areas", [])
    area_mgr = load_areas(areas_cfg)

    # 4) npcs (vía factory del llamador)
    npcs = []
    for npc_cfg in data.get("npcs", []):
        if "id" not in npc_cfg or "cell" not in npc_cfg:
            log.warning(f"NPC inválido (faltan 'id' o 'cell'): {npc_cfg!r}")
            continue
        try:
            npc = npc_factory(npc_cfg, object_mgr, area_mgr)
            npcs.append(npc)
        except Exception as e:
            log.warning(f"No se pudo crear NPC {npc_cfg.get('id')!r}: {e}")

    log.info(f"load_ok blocked={len(blocked_cells)} items={len(object_mgr.all())} npcs={len(npcs)} from={p}")

    blocked_cells |= area_mgr.perimeter_blocked_cells()

    if len(area_mgr):
        log.info(f"Cargadas {len(area_mgr)} áreas: {[a.id for a in area_mgr.areas()]}")
    else:
        log.info("No se definieron áreas en el JSON")

    return blocked_cells, object_mgr, npcs, area_mgr
