import pytest

from .model import Generator
from maptool.datatypes import Vec2, Box
from maptool.map import Map
from maptool.room import Room, RoomSide
from maptool.corridor import Corridor

NORTH = RoomSide.NORTH
WEST = RoomSide.WEST
SOUTH = RoomSide.SOUTH
EAST = RoomSide.EAST

@pytest.fixture
def emptymodel():
    g = Generator()
    g.generation = -1
    g._reset_generator(Map(Map.defaults()).gp)
    return g


@pytest.fixture
def rooms3_horizontal_spur():
    """
               (10,0)+--+
                     |r2|
                     +--+ (14,4)
                      
    (0,6)+--+         
         |r1|
         +--+ (4,10)
                   
            (6,12)+--+
                  |r3|
                  +--+ (10,16)

    """

    ox, oy = 2.0, 2.0
    def frombox(tl, br, **kw):
        return Room.frombox(Vec2(ox + tl.x, oy+tl.y), Vec2(ox+br.x, oy+br.y), corridors=[[], [], [], []], **kw)

    #             (10,0)+--+
    #                   |  |
    #                   +--+ (14,4)
    r2 = frombox(Vec2(10.0, 0.0), Vec2(14.0, 4.0))
    #                    ^
    #  (0,6)+--+         |
    #       |  |---------+
    #       +--+ (4,10)
    r1 = frombox(Vec2(0.0, 6.0), Vec2(4.0, 10.0))
    #                 |
    #          (6,12)+--+
    #                |  |
    #                +--+ (10,16)
    r3 = frombox(Vec2(6.0, 12.0), Vec2(10.0, 16.0))

    return r1, r2, r3

@pytest.fixture
def rooms3_horizontal_spur_inverted():
    """
    (0,0)+--+
         |r2|
         +--+ (4,4)
                   
                     (10,6)+--+         
                           |r1|
                           +--+ (14,10)
                   
           (4,12)+--+
                 |r3|
                 +--+ (10,16)
    """

    ox, oy = 2.0, 2.0
    def frombox(tl, br, **kw):
        return Room.frombox(Vec2(ox + tl.x, oy+tl.y), Vec2(ox+br.x, oy+br.y), corridors=[[], [], [], []], **kw)

    # (0,0)+--+
    #      |  |
    #      +--+ (4,4)
    r2 = frombox(Vec2(0.0, 0.0), Vec2(4.0, 4.0))
    #        ^                   
    #        |       (10,6)+--+         
    #        +-------------|  |
    #             |        +--+ (14,10)
    r1 = frombox(Vec2(10.0, 6.0), Vec2(14.0, 10.0))
    #             |
    #      (6,12)+--+
    #            |  |
    #            +--+ (10,16)
    r3 = frombox(Vec2(6.0, 12.0), Vec2(10.0, 16.0))

    return r1, r2, r3


@pytest.fixture
def spur_horizontal(emptymodel, rooms3_horizontal_spur):
    """
                 r2
                  + i2
                  |     Corridor A
    r1  i0+-------+ i1
    r1  j0+----+ j1     Corridor B
               |       <- spur is j1 - j2
               + j2
               r3
    """

    g = emptymodel
    r1, r2, r3 = rooms3_horizontal_spur

    ca = Corridor(
        points=[Vec2(4.0, 8.0), Vec2(12.0, 8.0), Vec2(12.0, 4.0)],
        joins=[0,1],
        join_sides=[EAST, SOUTH]
        )

    cb = Corridor(
        points=[Vec2(4.0, 8.0), Vec2(8.0, 8.0), Vec2(12.0, 4.0)],
        joins=[0,2],
        join_sides=[EAST, NORTH]
        )

    r2.corridors[SOUTH] = [0]
    r1.corridors[EAST] = [0, 1]
    r3.corridors[NORTH] = [1]

    g.rooms.extend([r1, r2, r3])
    g.corridors.extend([ca, cb])
    return g

@pytest.fixture
def spur_horizontal_opposed(emptymodel, rooms3_horizontal_spur):
    """
                 r2
                  + i2
                  |     Corridor A
    r1  i0+-------+ i1
    r1  j2+----+ j1     Corridor B
               |       <- spur is j1 - j2
               + j0
               r3
    """

    g = emptymodel
    r1, r2, r3 = rooms3_horizontal_spur

    ca = Corridor(
        points=[Vec2(4.0, 8.0), Vec2(12.0, 8.0), Vec2(12.0, 4.0)],
        joins=[0,1],
        join_sides=[EAST, SOUTH]
        )

    cb = Corridor(
        points=[Vec2(12.0, 4.0), Vec2(8.0, 8.0), Vec2(4.0, 8.0)],
        joins=[2, 0],
        join_sides=[NORTH, EAST]
        )

    r2.corridors[SOUTH] = [0]
    r1.corridors[EAST] = [0, 1]
    r3.corridors[NORTH] = [1]

    g.rooms.extend([r1, r2, r3])
    g.corridors.extend([ca, cb])
    return g



@pytest.fixture
def spur_horizontal_inverted(emptymodel, rooms3_horizontal_spur_inverted):
    """
     r2
      + i2
      |     
    i1+-------+ i0 r1  Corridor A
       j1+----+ j0     Corridor B
         |       <- spur is j0 - j1
         + j2
         r3
    """

    g = emptymodel
    r1, r2, r3 = rooms3_horizontal_spur_inverted

    ca = Corridor(
        points=[Vec2(10.0, 8.0), Vec2(2.0, 8.0), Vec2(2.0, 4.0)],
        joins=[0,1],
        join_sides=[WEST, SOUTH]
        )

    cb = Corridor(
        points=[Vec2(10.0, 8.0), Vec2(4.0, 8.0), Vec2(4.0, 12.0)],
        joins=[0,2],
        join_sides=[WEST, NORTH]
        )

    r2.corridors[SOUTH] = [0]
    r1.corridors[WEST] = [0, 1]
    r3.corridors[NORTH] = [1]

    g.rooms.extend([r1, r2, r3])
    g.corridors.extend([ca, cb])
    return g


@pytest.fixture
def spur_horizontal_inverted_opposed(emptymodel, rooms3_horizontal_spur_inverted):
    """
     r2
      + i2
      |     
    i1+-------+ i0 r1  Corridor A
       j1+----+ j2     Corridor B
         |       <- spur is j0 - j1
         + j0
         r3
    """

    g = emptymodel
    r1, r2, r3 = rooms3_horizontal_spur_inverted

    ca = Corridor(
        points=[Vec2(10.0, 8.0), Vec2(2.0, 8.0), Vec2(2.0, 4.0)],
        joins=[0,1],
        join_sides=[WEST, SOUTH]
        )

    cb = Corridor(
        points=[Vec2(4.0, 12.0), Vec2(4.0, 8.0), Vec2(10.0, 8.0)],
        joins=[2, 0],
        join_sides=[NORTH, WEST]
        )

    r2.corridors[SOUTH] = [0]
    r1.corridors[WEST] = [0, 1]
    r3.corridors[NORTH] = [1]

    g.rooms.extend([r1, r2, r3])
    g.corridors.extend([ca, cb])
    return g



class TestModel:


    def test_merge_spur_horizontal(self, spur_horizontal):
        """
                     r2
                      + i2
                      |     Corridor A
        r1  i0+-------+ i1
        r1  j0+----+ j1     Corridor B
                   |       <- spur is j1 - j2
                   + j2
                   r3
        """


        g = spur_horizontal

        g._generate_corridor_intersections()
        assert len(g.corridors) == 3
        assert len(g.rooms) == 4

        # check the new room
        rnew = g.rooms[3]
        assert rnew.is_intersection is True
        assert rnew.corridors[WEST] == [2] # new room west wall -> new corridor
        assert rnew.corridors[EAST] == [0] # new room east wall -> clipped major corridor (long leg)
        assert g.corridors[rnew.corridors[WEST][0]].clipped == 0
        assert g.corridors[rnew.corridors[EAST][0]].clipped != 0

        assert rnew.corridors[SOUTH] == [1] # new room south wall -> clipped spur corridor

        # check the new corridor
        cnew = g.corridors[2]
        assert cnew.joins[0] == 0
        assert cnew.joins[1] == 3
        assert cnew.join_sides[0] == EAST
        assert cnew.join_sides[1] == WEST


    def test_merge_spur_horizontal_opposed(self, spur_horizontal_opposed):
        """
                  + i2
                  |
        i0+-------+ i1
        j2+----+ j1
               |       <- spur is j1 - j0
               + j0
        """
        g = spur_horizontal_opposed

        g._generate_corridor_intersections()
        assert len(g.corridors) == 3
        assert len(g.rooms) == 4

        # check the new room
        rnew = g.rooms[3]
        assert rnew.is_intersection is True
        assert rnew.corridors[WEST] == [2] # new room west wall -> new corridor
        assert rnew.corridors[EAST] == [0] # new room east wall -> clipped major corridor (long leg)
        assert g.corridors[rnew.corridors[WEST][0]].clipped == 0
        assert g.corridors[rnew.corridors[EAST][0]].clipped != 0

        assert rnew.corridors[SOUTH] == [1] # new room south wall -> clipped spur corridor

        # check the new corridor
        cnew = g.corridors[2]
        assert cnew.joins[0] == 0
        assert cnew.joins[1] == 3
        assert cnew.join_sides[0] == EAST
        assert cnew.join_sides[1] == WEST

    def test_merge_spur_horizontal_inverted(self, spur_horizontal_inverted):
        """
        i2+
          |
        i1+-------+ i0
           j1+----+ j0
             |       <- spur is j1 - j0
             + j2
        """
        g = spur_horizontal_inverted

        g._generate_corridor_intersections()
        assert len(g.corridors) == 3
        assert len(g.rooms) == 4

        # check the new room
        rnew = g.rooms[3]
        assert rnew.is_intersection is True
        assert rnew.corridors[WEST] == [0] # new room west wall -> corridor A
        assert rnew.corridors[EAST] == [2] # new room east wall -> corridor new
        assert rnew.corridors[SOUTH] == [1] # new room south wall -> corridor B
        assert g.corridors[rnew.corridors[WEST][0]].clipped != 0 # corridor A clipped
        assert g.corridors[rnew.corridors[EAST][0]].clipped == 0 # new corridor
        assert g.corridors[rnew.corridors[SOUTH][0]].clipped != 0 # corridor B clipped

        # check the new corridor
        cnew = g.corridors[2]
        assert cnew.joins[0] == 0 # r1
        assert cnew.joins[1] == 3 # rnew
        assert cnew.join_sides[0] == WEST
        assert cnew.join_sides[1] == EAST


    def test_merge_spur_horizontal_inverted_opposed(self, spur_horizontal_inverted_opposed):
        """
         r2
          + i2
          |     
        i1+-------+ i0 r1  Corridor A
           j1+----+ j2     Corridor B
             |       <- spur is j0 - j1
             + j0
             r3
        """

        g = spur_horizontal_inverted_opposed

        g._generate_corridor_intersections()
        assert len(g.corridors) == 3
        assert len(g.rooms) == 4

        # check the new room
        rnew = g.rooms[3]
        assert rnew.is_intersection is True
        assert rnew.corridors[WEST] == [0] # new room west wall -> corridor A
        assert rnew.corridors[EAST] == [2] # new room east wall -> corridor new
        assert rnew.corridors[SOUTH] == [1] # new room south wall -> corridor B
        assert g.corridors[rnew.corridors[WEST][0]].clipped != 0 # corridor A clipped
        assert g.corridors[rnew.corridors[EAST][0]].clipped == 0 # new corridor
        assert g.corridors[rnew.corridors[SOUTH][0]].clipped != 0 # corridor B clipped

        # check the new corridor
        cnew = g.corridors[2]
        assert cnew.joins[0] == 0 # r1
        assert cnew.joins[1] == 3 # rnew
        assert cnew.join_sides[0] == WEST
        assert cnew.join_sides[1] == EAST

