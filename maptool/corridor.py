from re import I
from typing import List, Tuple, Set
from dataclasses import dataclass

from .datatypes import Error, Vec2
from maptool import geometry as g

@dataclass
class Corridor:
    # The corridor start and end.
    # If its an L, then there is a start, middle and and
    points: List[Vec2] = ()

    # L corridors have two possibilities. the one placed in points is the shorter
    alternate: List[Vec2] = ()

    # The two rooms joined by this corridor
    joins: List[int] = ()

    join_sides: Tuple[str] = ()
    alternate_join_sides: Tuple[str] = ()

    # An rooms, other than the joined rooms, crossed by the corridor
    # tuples of room, wall crossed, and corridor segment crosing. For L's segment may be 0 or 1
    crosses: List[Tuple[int, int, int]] = ()
    alternate_crosses: List[Tuple[int, int, int]] = ()

    # corridor entanglement resolution state follows

    # If we had to clip this corridor
    clipped: int = 0
    is_inserted: bool = False

    entangled: Set[int] = ()

    generation: int = 0

    @classmethod
    def from_encoding(cls, e):
        return Corridor(
            points = [Vec2(p[0], p[1]) for p in e['points']],
            joins = e['joins'][:],
            join_sides = e['join_sides'][:]
        )

    def check_entangled(self, co):

        # intersections have zero diameter, so co-incident end point is not enough on its own
        if g.pt_essentially_same(self.points[0], co.points[0]):
            if self.points[0].x == self.points[1].x and self.points[0].x == co.points[1].x:
                return True
            if self.points[0].y == self.points[1].y and self.points[0].y == co.points[1].y:
                return True

        if g.pt_essentially_same(self.points[0], co.points[-1]):
            opi = 0 if len(co.points) == 2 else 1
            if self.points[0].x == self.points[1].x and self.points[0].x == co.points[opi].x:
                return True
            if self.points[0].y == self.points[1].y and self.points[0].y == co.points[opi].y:
                return True

        if g.pt_essentially_same(self.points[-1], co.points[0]):
            if co.points[0].x == co.points[1].x and co.points[0].x == self.points[0 if len(self.points) == 2 else 1].x:
                return True
            if co.points[0].y == co.points[1].y and co.points[0].x == self.points[0 if len(self.points) == 2 else 1].y:
                return True

        if g.pt_essentially_same(self.points[-1], co.points[-1]):
            spi = 0 if len(self.points) == 2 else 1
            opi = 0 if len(co.points) == 2 else 1
            if self.points[-1].x == self.points[spi].x and self.points[-1].x == co.points[opi].x:
                return True
            if self.points[-1].y == self.points[spi].y and self.points[-1].y == co.points[opi].y:
                return True

    def entangle(self, i):
        if not self.entangled:
            self.entangled = set([])
        self.entangled.add(i)

    def encode(self):
        return dict(
            points=[(p.x, p.y) for p in self.points],
            joins=self.joins[:],
            join_sides=self.join_sides
        )