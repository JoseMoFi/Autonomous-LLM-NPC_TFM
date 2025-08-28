from src.world.areas.areas import RectArea, AreaStyle, CELL_SIZE

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
        label_px=CELL_SIZE,
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
        label_px=CELL_SIZE,
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
        label_px=CELL_SIZE,
    )