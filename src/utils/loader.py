# src/world/loader.py
from __future__ import annotations
from pathlib import Path
from typing import Callable, Iterable, Any

import json

from src.utils.logger import get_logger
from src.world.items import ObjectManager, Gem, Shard, Relic, WorldObject

log = get_logger("world.loader")

# ---- helpers de validación/normalización ----

def _as_cell(value: Any) -> tuple[int, int]:
    if (isinstance(value, (list, tuple)) and len(value) == 2
            and all(isinstance(v, (int, float)) for v in value)):
        # admitimos float pero truncamos a int por seguridad
        return int(value[0]), int(value[1])
    raise ValueError(f"Celda inválida: {value!r}")

def _item_from_cfg(cfg: dict) -> WorldObject:
    t = str(cfg.get("type", "")).lower().strip()
    cell = _as_cell(cfg.get("cell"))
    if t == "gem":
        return Gem(cell)
    if t == "shard":
        return Shard(cell)
    if t == "relic":
        return Relic(cell)
    raise ValueError(f"Tipo de item desconocido: {t!r}")

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
    om = ObjectManager()
    for item_cfg in data.get("items", []):
        try:
            om.add(_item_from_cfg(item_cfg))
        except Exception as e:
            log.warning(f"Item inválido {item_cfg!r}: {e}")

    # 3) npcs (vía factory del llamador)
    npcs = []
    for npc_cfg in data.get("npcs", []):
        if "id" not in npc_cfg or "cell" not in npc_cfg:
            log.warning(f"NPC inválido (faltan 'id' o 'cell'): {npc_cfg!r}")
            continue
        try:
            npc = npc_factory(npc_cfg)
            npcs.append(npc)
        except Exception as e:
            log.warning(f"No se pudo crear NPC {npc_cfg.get('id')!r}: {e}")

    log.info(f"load_ok blocked={len(blocked_cells)} items={len(om.all())} npcs={len(npcs)} from={p}")
    return blocked_cells, om, npcs
