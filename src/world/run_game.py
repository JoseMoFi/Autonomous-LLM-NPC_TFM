# src/world/run_game.py
from __future__ import annotations
import arcade
from .scene import GameWindow

def main() -> None:
    GameWindow()
    arcade.run()

if __name__ == "__main__":
    main()
