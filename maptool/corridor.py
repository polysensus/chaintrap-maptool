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

        for i, p in enumerate(self.points):
            for po in co.points:
                if g.pt_essentially_same(p, po):
                    # are any of the other self.points which have same x or y  as the co-incident point
                    for ii in range(len(self.points)):
                        if ii == i:
                            continue
                        if g.essentially_equal(po.x, self.points[ii].x):
                            return True
                        if g.essentially_equal(po.y, self.points[ii].y):
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