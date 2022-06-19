import pytest

from maptool.datatypes import Vec2
from maptool.room import Room, RoomSide
from maptool.corridor import Corridor

NORTH = RoomSide.NORTH
WEST = RoomSide.WEST
SOUTH = RoomSide.SOUTH
EAST = RoomSide.EAST


@pytest.fixture
def room3_horizontal_cross():
    """
               (6,0)+--+
                    |r2|
                    +--+ (10,4)

    (0,6)+--+             (12,6)+--+
         |r1|                   |r3|
         +--+ (4,10)            +--+ (16,10)
    """
    ox, oy = 0.0, 0.0

    def frombox(tl, br, **kw):
        return Room.frombox(
            Vec2(ox + tl.x, oy + tl.y),
            Vec2(ox + br.x, oy + br.y),
            corridors=[[], [], [], []],
            **kw
        )

    r2 = frombox(Vec2(6.0, 0.0), Vec2(10.0, 4.0))
    #             (6,0)
    #               +--+
    #               |r2|
    #               +--+ (10,4)
    r3 = frombox(Vec2(12.0, 6.0), Vec2(16.0, 10.0))
    #
    #  (0,6)+--+          (12,8)+--+
    #       |r1|               |r3|
    #       +--+               +--+
    #        (4,10)       (16,12)
    r1 = frombox(Vec2(0.0, 6.0), Vec2(4.0, 10.0))
    return r1, r2, r3


@pytest.fixture
def room4_horizontal_cross():
    """
               (6,0)+--+
                    |r2|
                    +--+ (10,4)

    (0,6)+--+             (12,6)+--+
         |r1|                   |r3|
         +--+ (4,10)            +--+ (16,10)

    (0,12)+--+
         |r4|
         +--+ (4,16)

    """
    ox, oy = 0.0, 0.0

    def frombox(tl, br, **kw):
        return Room.frombox(
            Vec2(ox + tl.x, oy + tl.y),
            Vec2(ox + br.x, oy + br.y),
            corridors=[[], [], [], []],
            **kw
        )

    r2 = frombox(Vec2(6.0, 0.0), Vec2(10.0, 4.0))
    #             (6,0)
    #               +--+
    #               |r2|
    #               +--+ (10,4)
    r3 = frombox(Vec2(12.0, 6.0), Vec2(16.0, 10.0))
    #
    #  (0,6)+--+          (12,8)+--+
    #       |r1|               |r3|
    #       +--+               +--+
    #        (4,10)       (16,12)
    #
    # (0,12)+--+
    #      |r4|
    #      +--+ (4,16)

    r1 = frombox(Vec2(0.0, 6.0), Vec2(4.0, 10.0))
    r4 = frombox(Vec2(0.0, 12.0), Vec2(4.0, 16.0))
    return r1, r2, r3, r4


@pytest.fixture
def room3_horizontal_converge():
    """
                               (14,0)+--+
                                    |r2|
                                    +--+ (18,4)

    (0,6)+--+
         |r1|         (6,8)+--+
         +--+ (4,10)        |r3|
                            +--+ (10,12)

    """
    ox, oy = 0.0, 0.0

    def frombox(tl, br, **kw):
        return Room.frombox(
            Vec2(ox + tl.x, oy + tl.y),
            Vec2(ox + br.x, oy + br.y),
            corridors=[[], [], [], []],
            **kw
        )

    r2 = frombox(Vec2(14.0, 0.0), Vec2(18.0, 4.0))
    #                      (14,0)
    #                         +--+
    #        .--------------->|r2|
    #        |           |    +--+ (18,4)
    r3 = frombox(Vec2(6.0, 8.0), Vec2(10.0, 12.0))
    #        |           |
    #  (0,6)+--+   (6,8)+--+
    #       |r1|        |r3|
    #       +--+        +--+
    #        (4,10)       (10,12)
    r1 = frombox(Vec2(0.0, 6.0), Vec2(4.0, 10.0))
    return r1, r2, r3


@pytest.fixture
def rooms3_horizontal_tee():
    """
               (10,0)+--+
                     |r2|
                     +--+ (14,4)

    (0,6)+--+
         |r1|
         +--+ (4,10)

            (10,12)  +--+
                     |r3|
                     +--+ (14,16)

    """

    ox, oy = 2.0, 2.0

    def frombox(tl, br, **kw):
        return Room.frombox(
            Vec2(ox + tl.x, oy + tl.y),
            Vec2(ox + br.x, oy + br.y),
            corridors=[[], [], [], []],
            **kw
        )

    #             (10,0)+--+
    #                   |  |
    #                   +--+ (14,4)
    r2 = frombox(Vec2(10.0, 0.0), Vec2(14.0, 4.0))
    #                    ^
    #  (0,6)+--+         |
    #       |  |---------+
    #       +--+ (4,10)
    r1 = frombox(Vec2(0.0, 6.0), Vec2(4.0, 10.0))
    #                    |
    #             (10,12)+--+
    #                   |  |
    #                   +--+ (14,16)
    r3 = frombox(Vec2(10.0, 12.0), Vec2(14.0, 16.0))

    return r1, r2, r3


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
        return Room.frombox(
            Vec2(ox + tl.x, oy + tl.y),
            Vec2(ox + br.x, oy + br.y),
            corridors=[[], [], [], []],
            **kw
        )

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
        return Room.frombox(
            Vec2(ox + tl.x, oy + tl.y),
            Vec2(ox + br.x, oy + br.y),
            corridors=[[], [], [], []],
            **kw
        )

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
        joins=[0, 1],
        join_sides=[EAST, SOUTH],
    )

    cb = Corridor(
        points=[Vec2(4.0, 8.0), Vec2(8.0, 8.0), Vec2(8.0, 12.0)],
        joins=[0, 2],
        join_sides=[EAST, NORTH],
    )

    r2.corridors[SOUTH] = [0]
    r1.corridors[EAST] = [0, 1]
    r3.corridors[NORTH] = [1]

    g.rooms.extend([r1, r2, r3])
    g.corridors.extend([ca, cb])

    return g


@pytest.fixture
def spur_horizontal_11(emptymodel, rooms3_horizontal_spur):
    """
                 r2
                  + i0
                  |     Corridor A
    r1  i2+-------+ i1
    r1  j2+----+ j1     Corridor B
               |       <- spur is j1 - j2
               + j0
               r3
    """

    g = emptymodel
    r1, r2, r3 = rooms3_horizontal_spur

    ca = Corridor(
        points=[Vec2(12.0, 4.0), Vec2(12.0, 8.0), Vec2(4.0, 8.0)],
        joins=[1, 0],
        join_sides=[SOUTH, EAST],
    )

    cb = Corridor(
        points=[Vec2(8.0, 12.0), Vec2(8.0, 8.0), Vec2(4.0, 8.0)],
        joins=[2, 0],
        join_sides=[NORTH, EAST],
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
        joins=[0, 1],
        join_sides=[EAST, SOUTH],
    )

    cb = Corridor(
        points=[Vec2(8.0, 12.0), Vec2(8.0, 8.0), Vec2(4.0, 8.0)],
        joins=[2, 0],
        join_sides=[NORTH, EAST],
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
        joins=[0, 1],
        join_sides=[WEST, SOUTH],
    )

    cb = Corridor(
        points=[Vec2(10.0, 8.0), Vec2(4.0, 8.0), Vec2(4.0, 12.0)],
        joins=[0, 2],
        join_sides=[WEST, NORTH],
    )

    r2.corridors[SOUTH] = [0]
    r1.corridors[WEST] = [0, 1]
    r3.corridors[NORTH] = [1]

    g.rooms.extend([r1, r2, r3])
    g.corridors.extend([ca, cb])
    return g
