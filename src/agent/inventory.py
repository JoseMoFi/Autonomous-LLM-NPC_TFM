from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict

@dataclass
class Inventory:
    items: Dict[str, int] = field(default_factory=dict)

    def count(self, item: str) -> int:
        return self.items.get(item, 0)

    def has(self, req: Dict[str, int]) -> bool:
        return all(self.count(k) >= v for k, v in req.items())

    def add(self, delta: Dict[str, int]) -> None:
        for k, v in delta.items():
            if v <= 0: 
                continue
            self.items[k] = self.count(k) + v

    def remove(self, req: Dict[str, int]) -> bool:
        if not self.has(req):
            return False
        for k, v in req.items():
            newv = self.count(k) - v
            if newv <= 0:
                self.items.pop(k, None)
            else:
                self.items[k] = newv
        return True
