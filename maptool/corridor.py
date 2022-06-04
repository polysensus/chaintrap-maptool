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
    # True if the elbows of each L are essentially equal. two such corridors
    # will merge to 3 straight sections rather than the usual L + 2 straight
    entangled_even: bool = False

    generation: int = 0

    def entangle(self, i):
        if not self.entangled:
            self.entangled = set([])
        self.entangled.add(i)
