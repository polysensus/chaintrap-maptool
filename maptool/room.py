from typing import List
from dataclasses import dataclass
from .datatypes import Vec2, Box, GenSpace
from maptool import geometry as g


@dataclass
class GenRoom(GenSpace):
    pass

class RoomSide:
    NORTH: int = g.TOP
    WEST: int = g.LEFT
    SOUTH: int = g.BOTTOM
    EAST: int = g.RIGHT

    @classmethod
    def opposite(cls, side: int) -> int:
        return (side + 2) % 4

    @classmethod
    def name(cls, side: int) -> str:
        return { 
            RoomSide.NORTH: "north",
            RoomSide.WEST: "west",
            RoomSide.SOUTH: "south",
            RoomSide.EAST: "east"
        }[side]

SIDES = [RoomSide.NORTH, RoomSide.WEST, RoomSide.SOUTH, RoomSide.EAST]
class SRoomSide:
    NORTH: str = 'NORTH'
    WEST: str = 'WEST'
    SOUTH: str = 'SOUTH'
    EAST: str = 'SOUTH'

@dataclass
class Room:
    center: Vec2 = Vec2()
    width: float = 0.0
    length: float = 0.0
    is_main: bool = False
    # if the room is an intersection the width and lenght should be ingored - its part of the corridors it joins
    is_intersection: bool = False
    # corridors[NORTH, WEST, SOUTH, EAST]]
    corridors: List[List[int]] = ()

    def __init__(self, center=Vec2(), width=0.0, length=0.0, is_main=False, is_intersection=False, corridors=None):
        self.center = center
        self.width = width
        self.length = length
        self.is_main = is_main
        self.corridors = corridors
        self.is_intersection = is_intersection
        if self.corridors is None:
            self.corridors = [[], [], [], []]

    @classmethod
    def frombox(cls, tl: Vec2, br: Vec2, **kw):
        center = Vec2((tl.x + br.x) / 2.0, (tl.y + br.y) / 2.0)
        w = br.x - tl.x if br.x > tl.x else tl.x - br.x
        ln = br.y - tl.y if br.y > tl.y else tl.y - br.y
        return cls(center, w, ln, **kw)


    @classmethod
    def from_encoding(cls, d):

        return cls(
            center = Vec2(d["x"], d["y"]),
            width = d["w"],
            length = d["l"],
            is_intersection = d["inter"],
            is_main = d["main"],
            corridors = [
                d["corridors"][0][:],
                d["corridors"][1][:],
                d["corridors"][2][:],
                d["corridors"][3][:]]
        )

    def encode(self):
        return dict(
            x=self.center.x,
            y=self.center.y,
            w=self.width,
            l=self.length,
            inter=self.is_intersection,
            main=self.is_main,
            corridors=[self.corridors[0][:],self.corridors[1][:],self.corridors[2][:],self.corridors[3][:]]
        )

    def topleft(self) -> Vec2:
        x = self.center.x - (self.width / 2)
        y = self.center.y - (self.length / 2)
        return Vec2(x, y)

    def bottomright(self) -> Vec2:
        x = self.center.x + (self.width / 2)
        y = self.center.y + (self.length / 2)
        return Vec2(x, y)

    def euclidean_dist(self, other) -> float:
        return g.pt_dist(self.center, other.center)


    def attached_side(self, icor) -> int:
        """Determine which side, if any, icor is present on
        """
        for side, axis in enumerate(self.corridors):
            try:
                i = axis.index(icor)
                return side
            except ValueError:
                continue
        return None

    def detach_corridor(self, icor) -> int:
        """When reconciling entangled corridors we make special intersection rooms

        this method detaches the corridor identified by icor or raises KeyError
        if it is not found entering any side of the room
        
        when we do that we need to detach the corridor from the old room and
        attach to the intersection.  Note that its not geometrically possible
        for a corridor to be attached to multiple sides of the same room"""

        for side, axis in enumerate(self.corridors):
            try:
                i = axis.index(icor)
                axis.pop(i)
                return side
            except ValueError:
                continue
        raise KeyError(f"corridor {icor} not found")

    def corridor_side(self, icor):
        for side, axis in enumerate(self.corridors):
            try:
                axis.index(icor)
                return side
            except ValueError:
                continue
        raise KeyError(f"corridor {icor} not found in room {self.id}")



def rooms_check_line(rooms, line, *ignore) -> int:

    for i, r in enumerate(rooms):

        if i in ignore:
            continue

        room_box = Box(r.topleft(), r.bottomright())
        # coridors are 3 points
        for j in range(len(line) - 1):
            p1, p2 = line[j], line[j+1]
            if g.check_box_line(room_box, p1, p2) >=0:
                return i
    return False

def rooms_crossing_line(rooms, line, *ignore):

    for i, r in enumerate(rooms):

        if i in ignore:
            continue

        room_box = Box(r.topleft(), r.bottomright())
        # coridors are 3 points
        for j in range(len(line) - 1):
            p1, p2 = line[j], line[j+1]
            wall = g.check_box_line(room_box, p1, p2)
            if wall != -1:
                yield (i, wall, j)

def rooms_bbox(rooms) -> Box:

    minx, miny = None, None
    maxx, maxy = None, None

    avgw = 0
    avgl = 0

    for r in rooms:

        tl = r.topleft()
        br = r.bottomright()

        avgw += r.width
        avgl += r.length

        if minx is None:
            minx = tl.x
        elif tl.x < minx:
            minx = tl.x

        if miny is None:
            miny = tl.y
        elif tl.y < miny:
            miny = tl.y

        if maxx is None:
            maxx = br.x
        elif br.x > maxx:
            maxx = br.x

        if maxy is None:
            maxy = br.y
        elif br.y > maxy:
            maxy = br.y

    avgw /= len(rooms)
    avgl /= len(rooms)

    tl = Vec2(minx, miny)
    br = Vec2(maxx, maxy)
    return Box(tl, br), Vec2(avgw, avgl)
