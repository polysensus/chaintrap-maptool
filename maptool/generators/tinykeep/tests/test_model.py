import pytest

from maptool.datatypes import Vec2
from maptool.room import Room, RoomSide
from maptool.corridor import Corridor
from maptool.geometry import *

NORTH = RoomSide.NORTH
WEST = RoomSide.WEST
SOUTH = RoomSide.SOUTH
EAST = RoomSide.EAST

class TestModel:

    def test_merge_tee_horizontal(self, emptymodel, rooms3_horizontal_tee):
        """
        This is a rare case
                     r2
                      + i2
                      |     Corridor A
        r1  i0+-------+ i1
        r1  j0+-------+ j1     Corridor B
                      |        <- spur is j1 - j2
                      + j2
                      r3

                      |
            +---------+  results in 3 straights
                      |
        """

        # --- setup
        g = emptymodel
        r1, r2, r3 = rooms3_horizontal_tee

        ca = Corridor(
            points=[r1.pt_right(), None, r2.pt_bottom()],
            joins=[0,1],
            join_sides=[EAST, SOUTH]
            )
        ca.points[1] = Vec2(ca.points[2].x, ca.points[0].y)

        cb = Corridor(
            points=[r1.pt_right(), None, r3.pt_top()],
            joins=[0,2],
            join_sides=[EAST, NORTH]
            )
        cb.points[1] = Vec2(cb.points[2].x, cb.points[0].y)

        r2.corridors[SOUTH] = [0]
        r1.corridors[EAST] = [0, 1]
        r3.corridors[NORTH] = [1]

        g.rooms.extend([r1, r2, r3])
        g.corridors.extend([ca, cb])

        # --- test
        g._generate_intersections()
        assert len(g.corridors) == 3
        assert len(g.rooms) == 4

        cn = g.corridors[-1]
        rn = g.rooms[-1]
        irn = len(g.rooms) - 1

        assert cn.join_sides == [EAST, WEST]
        assert cn.joins == [0, irn]
        assert essentially_equal(cn.points[1].x, rn.center.x)
        assert essentially_equal(cn.points[1].y, rn.center.y)

        assert ca.join_sides == [NORTH, SOUTH]
        assert ca.joins == [irn, 1]
        assert pt_essentially_same(ca.points[0], rn.center)

        assert cb.join_sides == [SOUTH, NORTH]
        assert cb.joins == [irn, 2]
        assert pt_essentially_same(cb.points[0], rn.center)


    def test_merge_ll_converge_right(self, emptymodel, room3_horizontal_converge):
        """
        .----------+ r2  ca
        |     .----+     cb
        |     |
        +i0   +j0
        r1    r3

           ca rn  cn
        .-----+-----+ r2  ca
        |     |cb
        +i0   +j0
        r1    r3

        """

        # --- setup
        g = emptymodel
        r1, r2, r3 = room3_horizontal_converge

        ca = Corridor(
            points=[r1.pt_top(), None, r2.pt_left()],
            joins=[0,1],
            join_sides=[NORTH, WEST]
            )
        ca.points[1] = Vec2(ca.points[0].x, ca.points[2].y)

        cb = Corridor(
            points=[r3.pt_top(), None, r2.pt_left()],
            joins=[2,1],
            join_sides=[NORTH, WEST]
            )

        cb.points[1] = Vec2(cb.points[0].x, cb.points[2].y)

        g.rooms.extend([r1, r2, r3])
        g.corridors.extend([ca, cb])

        r1.corridors[NORTH] = [0]
        r2.corridors[WEST] = [0, 1]
        r3.corridors[NORTH] = [1]

        # --- test
        g._generate_intersections()
        assert len(g.corridors) == 3
        assert len(g.rooms) == 4

        cn = g.corridors[-1]
        rn = g.rooms[-1]
        irn = len(g.rooms) - 1

        assert cn.join_sides == [EAST, WEST]
        assert cn.joins == [irn, 1]
        assert essentially_equal(cn.points[0].x, rn.center.x)
        assert essentially_equal(cn.points[0].y, rn.center.y)
        assert essentially_equal(cn.points[-1].x, r2.pt_left().x)

        assert ca.join_sides == [NORTH, WEST]
        assert ca.joins == [0, irn]
        assert pt_essentially_same(ca.points[-1], rn.center)

        assert cb.join_sides == [NORTH, SOUTH]
        assert cb.joins == [2, irn]
        assert pt_essentially_same(cb.points[-1], rn.center)


    def test_merge_l_hlong(self, emptymodel, rooms3_horizontal_spur):
        """
                     r2
                      + i2
                      |     Corridor A
        r1  i0+-------+ i1
        r1  j1+------------+ j0     Corridor B
                             r3

               ca
              r2
            cn|  cb
         r1+--+----+ r3
              ri

        """

        g = emptymodel
        r1, r2, r3 = rooms3_horizontal_spur

        ca = Corridor(
            points=[Vec2(4.0, 8.0), Vec2(8.0, 8.0), Vec2(8.0, 4.0)],
            joins=[0,1],
            join_sides=[EAST, SOUTH]
            )

        cb = Corridor(
            points=[Vec2(12.0, 8.0), Vec2(4.0, 8.0)],
            joins=[2, 0],
            join_sides=[WEST, EAST]
            )

        r2.corridors[SOUTH] = [0]
        r1.corridors[EAST] = [0, 1]
        r3.corridors[WEST] = [1]

        g.rooms.extend([r1, r2, r3])
        g.corridors.extend([ca, cb])

        ca = g.corridors[0]
        cb = g.corridors[1]

        assert ca.joins[0] == 0
        assert ca.joins[1] == 1

        assert cb.joins[0] == 2
        assert cb.joins[1] == 0

        g._generate_intersections()
        assert len(g.corridors) == 3
        assert len(g.rooms) == 4

        cn = g.corridors[2]

        assert ca.joins[0] == 3
        assert ca.joins[1] == 1

        assert cb.joins[0] == 2
        assert cb.joins[1] == 3
        assert cn.joins[1] == 3
        assert cn.join_sides[0] == RIGHT
        assert cn.join_sides[1] == LEFT
        assert cn.joins[0] == 0


    def test_merge_l_hshort(self, emptymodel, rooms3_horizontal_spur):
        """
                     r2
                      + i2
                      |     Corridor A
        r1  i0+-------+ i1
        r1  j0+----+ j1     Corridor B
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
            points=[Vec2(4.0, 8.0), Vec2(8.0, 8.0)],
            joins=[0,2],
            join_sides=[EAST, WEST]
            )

        r2.corridors[SOUTH] = [0]
        r1.corridors[EAST] = [0, 1]
        r3.corridors[WEST] = [1]

        g.rooms.extend([r1, r2, r3])
        g.corridors.extend([ca, cb])

        ca = g.corridors[0]
        cb = g.corridors[1]

        assert ca.joins[0] == 0
        assert ca.joins[1] == 1

        assert cb.joins[0] == 0
        assert cb.joins[1] == 2

        g._generate_intersections()
        assert len(g.corridors) == 2
        assert len(g.rooms) == 3

        assert ca.joins[0] == 2
        assert ca.joins[1] == 1

        assert cb.joins[0] == 0
        assert cb.joins[1] == 2


    def test_merge_l_inv_hshort(self, emptymodel, rooms3_horizontal_spur):
        """
                     r2
                      + i0
                      |     Corridor A
        r1  i2+-------+ i1
        r1  j0+----+ j1     Corridor B
                   r3

                r2
                |
        r1+--+--+
             r3

        """

        g = emptymodel
        r1, r2, r3 = rooms3_horizontal_spur

        ca = Corridor(
            points=[Vec2(12.0, 4.0), Vec2(12.0, 8.0), Vec2(4.0, 8.0)],
            joins=[1,0],
            join_sides=[SOUTH, EAST]
            )

        cb = Corridor(
            points=[Vec2(4.0, 8.0), Vec2(8.0, 8.0)],
            joins=[0,2],
            join_sides=[EAST, WEST]
            )

        r2.corridors[SOUTH] = [0]
        r1.corridors[EAST] = [0, 1]
        r3.corridors[WEST] = [1]

        g.rooms.extend([r1, r2, r3])
        g.corridors.extend([ca, cb])

        ca = g.corridors[0]
        cb = g.corridors[1]

        assert ca.joins[0] == 1
        assert ca.joins[1] == 0

        assert cb.joins[0] == 0
        assert cb.joins[1] == 2

        g._generate_intersections()
        assert len(g.corridors) == 2
        assert len(g.rooms) == 3

        assert ca.joins[0] == 1
        assert ca.joins[1] == 2

        assert cb.joins[0] == 0
 

    def test_merge_l_hshort_inv(self, emptymodel, rooms3_horizontal_spur):
        """
                     r2
                      + i2
                      |     Corridor A
        r1  i0+-------+ i1
        r1  j1+----+ j0     Corridor B
                   r3

                r2
                |
        r1+--+--+
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
            points=[Vec2(8.0, 8.0), Vec2(4.0, 8.0)],
            joins=[2, 0],
            join_sides=[WEST, EAST]
            )

        r2.corridors[SOUTH] = [0]
        r1.corridors[EAST] = [0, 1]
        r3.corridors[WEST] = [1]

        g.rooms.extend([r1, r2, r3])
        g.corridors.extend([ca, cb])

        ca = g.corridors[0]
        cb = g.corridors[1]

        assert ca.joins[0] == 0
        assert ca.joins[1] == 1

        assert cb.joins[0] == 2
        assert cb.joins[1] == 0

        g._generate_intersections()
        assert len(g.corridors) == 2
        assert len(g.rooms) == 3

        assert ca.joins[0] == 2
        assert ca.joins[1] == 1

        assert cb.joins[0] == 2
        assert cb.joins[1] == 0


    def test_merge_l_inv_hshort_inv(self, emptymodel, rooms3_horizontal_spur):
        """
                     r2
                      + i0
                      |     Corridor A
        r1  i2+-------+ i1
        r1  j2+----+ j0     Corridor B
                   r3

                    r2
                    |
            r1+--+--+
                 r3
        """

        g = emptymodel
        r1, r2, r3 = rooms3_horizontal_spur

        ca = Corridor(
            points=[Vec2(12.0, 4.0), Vec2(12.0, 8.0), Vec2(4.0, 8.0)],
            joins=[1,0],
            join_sides=[SOUTH, EAST]
            )

        cb = Corridor(
            points=[Vec2(8.0, 8.0), Vec2(4.0, 8.0)],
            joins=[2, 0],
            join_sides=[WEST, EAST]
            )

        r2.corridors[SOUTH] = [0]
        r1.corridors[EAST] = [0, 1]
        r3.corridors[WEST] = [1]

        g.rooms.extend([r1, r2, r3])
        g.corridors.extend([ca, cb])

        ca = g.corridors[0]
        cb = g.corridors[1]

        assert ca.joins[0] == 1
        assert ca.joins[1] == 0

        assert cb.joins[0] == 2
        assert cb.joins[1] == 0

        g._generate_intersections()
        assert len(g.corridors) == 2
        assert len(g.rooms) == 3

        assert ca.joins[0] == 1
        assert ca.joins[1] == 2
        assert ca.join_sides[0] == SOUTH
        assert ca.join_sides[1] == EAST

        assert cb.joins[0] == 2
        assert cb.joins[1] == 0


    def test_merge_spur_horizontal(self, emptymodel, rooms3_horizontal_spur):
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
            points=[Vec2(4.0, 8.0), Vec2(8.0, 8.0), Vec2(8.0, 12.0)],
            joins=[0,2],
            join_sides=[EAST, NORTH]
            )

        r2.corridors[SOUTH] = [0]
        r1.corridors[EAST] = [0, 1]
        r3.corridors[NORTH] = [1]

        g.rooms.extend([r1, r2, r3])
        g.corridors.extend([ca, cb])

        ca = g.corridors[0]
        cb = g.corridors[1]

        assert ca.join_sides[0] == EAST
        assert ca.join_sides[1] == SOUTH
        assert cb.join_sides[0] == EAST
        assert cb.join_sides[1] == NORTH

        # assert the test data is the shape we expect
        assert essentially_equal(ca.points[0].y, ca.points[1].y)
        assert essentially_equal(ca.points[1].x, ca.points[2].x)
        assert essentially_equal(cb.points[0].y, cb.points[1].y)
        assert essentially_equal(cb.points[1].x, cb.points[2].x)

        assert pt_essentially_same(ca.points[0], cb.points[0])
        assert pt_dist2(cb.points[0], cb.points[1]) < pt_dist2(ca.points[0], ca.points[1])

        g._generate_intersections()
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

        # check the spur
        assert cb.join_sides[0] == SOUTH
        assert cb.join_sides[1] == NORTH

        # check the clipped corridor
        assert ca.join_sides[0] == EAST
        assert ca.join_sides[1] == SOUTH

        assert cb.joins[0] == 3
        assert cb.joins[1] == 2


    def test_merge_spur_horizontal_11(self, emptymodel, rooms3_horizontal_spur):
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
            join_sides=[SOUTH, EAST]
            )

        cb = Corridor(
            points=[Vec2(8.0, 12.0), Vec2(8.0, 8.0), Vec2(4.0, 8.0)],
            joins=[2, 0],
            join_sides=[NORTH, EAST]
            )

        r2.corridors[SOUTH] = [0]
        r1.corridors[EAST] = [0, 1]
        r3.corridors[NORTH] = [1]

        g.rooms.extend([r1, r2, r3])
        g.corridors.extend([ca, cb])

        ca = g.corridors[0]
        cb = g.corridors[1]

        assert ca.join_sides[0] == SOUTH 
        assert ca.join_sides[1] == EAST
        assert cb.join_sides[0] == NORTH
        assert cb.join_sides[1] == EAST

        # assert the test data is the shape we expect
        assert essentially_equal(ca.points[1].y, ca.points[2].y)
        assert essentially_equal(ca.points[0].x, ca.points[1].x)
        assert essentially_equal(cb.points[1].y, cb.points[2].y)
        assert essentially_equal(cb.points[0].x, cb.points[1].x)

        assert pt_essentially_same(ca.points[2], cb.points[2])
        # assert pt_dist2(ca.points[1], ca.points[2]) > pt_dist2(cb.points[1], cb.points[2])
        assert pt_dist2(cb.points[1], cb.points[2]) < pt_dist2(ca.points[1], ca.points[2])

        # merge the corridors
        g._generate_intersections()
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
        assert cnew.joins[0] == 3
        assert cnew.joins[1] == 0
        assert cnew.join_sides[0] == WEST 
        assert cnew.join_sides[1] == EAST

        # check the clipped side
        assert ca.join_sides[0] == SOUTH
        assert ca.join_sides[1] == EAST

        # check the spur
        assert cb.join_sides[0] == NORTH
        assert cb.join_sides[1] == SOUTH 
        assert cb.joins[0] == 2
        assert cb.joins[1] == 3


    def test_merge_spur_horizontal_opposed(self, emptymodel, rooms3_horizontal_spur):
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
            points=[Vec2(8.0, 12.0), Vec2(8.0, 8.0), Vec2(4.0, 8.0)],
            joins=[2, 0],
            join_sides=[NORTH, EAST]
            )

        r2.corridors[SOUTH] = [0]
        r1.corridors[EAST] = [0, 1]
        r3.corridors[NORTH] = [1]

        g.rooms.extend([r1, r2, r3])
        g.corridors.extend([ca, cb])


        ca = g.corridors[0]
        cb = g.corridors[1]

        assert ca.join_sides[0] == EAST
        assert ca.join_sides[1] == SOUTH

        assert cb.join_sides[0] == NORTH
        assert cb.join_sides[1] == EAST

        g._generate_intersections()
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
        assert cnew.joins[0] == 3
        assert cnew.joins[1] == 0
        assert cnew.join_sides[0] == WEST
        assert cnew.join_sides[1] == EAST

        # check the clipped side
        assert ca.join_sides[0] == EAST
        assert ca.join_sides[1] == SOUTH

        # check the spur
        assert cb.join_sides[0] == NORTH
        assert cb.join_sides[1] == SOUTH 
        assert cb.joins[0] == 2
        assert cb.joins[1] == 3


    def test_merge_spur_horizontal_inverted(self, emptymodel, rooms3_horizontal_spur_inverted):
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

        ca = g.corridors[0]
        cb = g.corridors[1]

        # major side
        assert ca.join_sides[0] == WEST
        assert ca.join_sides[1] == SOUTH

        # spur
        assert cb.join_sides[0] == WEST
        assert cb.join_sides[1] == NORTH

        g._generate_intersections()
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
        assert cnew.joins[0] == 0
        assert cnew.joins[1] == 3
        assert cnew.join_sides[0] == WEST
        assert cnew.join_sides[1] == EAST

        # major side
        assert ca.join_sides[0] == WEST
        assert ca.join_sides[1] == SOUTH

        # spur
        assert cb.join_sides[0] == SOUTH
        assert cb.join_sides[1] == NORTH
        assert cb.joins[0] == 3
        assert cb.joins[1] == 2


    def test_merge_spur_horizontal_inverted_opposed(self, emptymodel, rooms3_horizontal_spur_inverted):
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

        ca = g.corridors[0]
        cb = g.corridors[1]

        # major side
        assert ca.join_sides[0] == WEST
        assert ca.join_sides[1] == SOUTH

        # spur
        assert cb.join_sides[0] == NORTH
        assert cb.join_sides[1] == WEST

        g._generate_intersections()
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
        assert cnew.joins[0] == 3 # rnew
        assert cnew.joins[1] == 0
        assert cnew.join_sides[0] == EAST
        assert cnew.join_sides[1] == WEST

        # major side
        assert ca.join_sides[0] == WEST
        assert ca.join_sides[1] == SOUTH

        # spur
        assert len(cb.points) == 2
        assert essentially_equal(cb.points[1].y, cnew.points[0].y)
        assert essentially_equal(cb.points[1].y, cnew.points[1].y)

        assert cb.join_sides[0] == NORTH
        assert cb.join_sides[1] == SOUTH
        assert cb.joins[0] == 2
        assert cb.joins[1] == 3


