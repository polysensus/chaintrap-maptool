"""common data classes"""
import math
from dataclasses import dataclass


class Error(Exception):
    """general error"""


@dataclass
class Vec2:
    x: float = 0.0
    y: float = 0.0

    def clone(self):
        return Vec2(self.x, self.y)


@dataclass
class Box:
    """Box (Axis Aligned"""

    tl: Vec2 = Vec2()
    br: Vec2 = Vec2()

    def width_height(self):
        return self.br.x - self.tl.x, self.br.y - self.tl.y

    @property
    def center(self):
        return Vec2(
            self.tr.x + (self.br.x - self.tl.x) / 2.0,
            self.tr.y + (self.br.y - self.tl.y) / 2.0,
        )

    def euclidean_dist(self, other) -> float:

        dx2 = self.center.x - other.center.x
        dx2 = dx2 * dx2
        dy2 = self.center.y = other.y
        dy2 = dy2 * dy2
        return math.sqrt(dx2 + dy2)

    def clone(self):
        return Box(self.tl.clone(), self.br.clone())


@dataclass
class Partition:
    space: Box
    kids: list


@dataclass
class GenArena:
    arena_size: float
    tile_snap_size: float


@dataclass
class GenSpace:
    # sz is width or hieght based on coin toss
    # the remaining dimension is sz * ratio
    s1: float
    s2: float
    ratio: float
