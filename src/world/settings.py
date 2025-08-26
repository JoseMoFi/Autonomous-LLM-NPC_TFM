# src/world/settings.py
from dataclasses import dataclass

@dataclass(frozen=True)
class WorldSettings:
    WIDTH: int = 1280
    HEIGHT: int = 720
    GRID_SIZE: int = 24
    FPS: int = 60

SETTINGS = WorldSettings()
