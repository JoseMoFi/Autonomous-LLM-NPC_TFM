import arcade

from src.world.items import WorldObject
from src.world.grid import Cell


class Wheat(WorldObject):
    def __init__(self, cell: Cell):
        super().__init__(cell=cell, color=arcade.color.YELLOW, name="wheat")

class Bread(WorldObject):
    def __init__(self, cell: Cell):
        # Si prefieres otro tono: arcade.color.SADDLE_BROWN o BURLYWOOD
        super().__init__(cell=cell, color=arcade.color.BROWN, name="bread")


    # --- Registro de tipos y factory por string ---
ITEM_CLASSES = {
    "wheat": Wheat,
    "bread": Bread,
}

def make_item(item_type: str, cell: Cell) -> WorldObject:
    cls = ITEM_CLASSES.get(item_type.lower())
    if cls is None:
        raise ValueError(f"Unknown item type: {item_type}")
    return cls(cell)