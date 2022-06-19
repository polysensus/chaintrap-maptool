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

    @classmethod
    def from_encoding(cls, e):
        return Corridor(
            points=[Vec2(p[0], p[1]) for p in e["points"]],
            joins=e["joins"][:],
            join_sides=e["join_sides"][:],
        )

    def check_entangled(self, co, margin=0.1, margin_factor=None):
        """check for pairs of co-linear corridor segments"""

        for i in range(2):

            if i + 1 >= len(self.points):
                continue
            lap1, lap2 = self.points[i], self.points[i + 1]

            for j in range(2):
                if j + 1 >= len(co.points):
                    continue
                lbp1, lbp2 = co.points[j], co.points[j + 1]

                # p1 and p2 will be the points of la or None if they are not on lb
                opposed = False
                ok, p1, p2 = g.xline_in_line(
                    lap1, lap2, lbp1, lbp2, margin=margin, margin_factor=margin_factor
                )
                if ok and not (p1 and p2):
                    opposed = True
                    # try the otherway round - if lap1 -> lap2 is longer lap2 will be off the line
                    ok, p1, p2 = g.xline_in_line(
                        lbp1,
                        lbp2,
                        lap1,
                        lap2,
                        margin=margin,
                        margin_factor=margin_factor,
                    )

                # For an entanglement we need two points of intersection
                if ok and p1 and p2:
                    return (p1, p2, i, j, opposed)
        return False

    def check_crossing(self, co):
        """check for pairs of intersecting corridor segments"""

        for i in range(2):

            if i + 1 >= len(self.points):
                continue
            lap1, lap2 = self.points[i], self.points[i + 1]

            for j in range(2):
                if j + 1 >= len(co.points):
                    continue
                lbp1, lbp2 = co.points[j], co.points[j + 1]

                ok, pi = g.line_line(lap1, lap2, lbp1, lbp2)
                if ok:
                    endpoint = False
                    for lp in [lap1, lap2, lbp1, lbp2]:
                        if g.pt_essentially_same(pi, lp):
                            endpoint = True
                            break
                    if not endpoint:
                        return (i, j, pi)

        return None

    def entangle(self, i):
        if not self.entangled:
            self.entangled = set([])
        self.entangled.add(i)

    def encode(self):
        return dict(
            points=[(p.x, p.y) for p in self.points],
            joins=self.joins[:],
            join_sides=self.join_sides,
        )
