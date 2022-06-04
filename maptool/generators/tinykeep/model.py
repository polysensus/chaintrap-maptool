"""generative, simulation based, model"""
import enum
from ntpath import join
import sys
import json
import math
import random
from dataclasses import dataclass

import numpy as np
import scipy
from scipy.spatial import Delaunay

from maptool.datatypes import GenArena, Vec2, Box
from maptool.randprimitives import rand_room
from maptool.room import GenRoom, Room, RoomSide, rooms_crossing_line
from maptool.corridor import Corridor

from maptool import geometry as g

from .flock import Boid
from .view_svg import Viewer, RenderOpts


class Error(Exception):
    """general error in the tinykeep model"""


def clip_indices(isegment):
    if isegment == 0:
        return 1, 2, 0
    else:
        return 0, 1, 2


class Generator:

    NAME = "tinykeep"

    """
    https://www.gamedeveloper.com/programming/procedural-dungeon-generation-algorithm
    """

    def __init__(self, debug=False):
        self.debug = debug
        self.debug_room_graph = False

    def _reset_generator(self, gp):
        self._generated = False
        self._loaded = False
        self.gp = gp
        self.ag = GenArena(self.gp.arena_size, self.gp.tile_snap_size)
        self.rg = GenRoom(self.gp.room_szmin, self.gp.room_szmax, self.gp.room_szratio)

        self.rooms = []
        self.corridors = []

        # room index tuple -> corridor index
        self.joined_rooms = dict()
        self.imain_rooms = []
        self.isecondary_rooms = []
        self.room_graph = dict()

        self.delaunay_tri_points = None
        self.delaunay_room_indices = None
        self.delaunay_mesh = None
        self.main_room_mst_points = None
        self.main_room_mst_connections = None  # keys will be (i,j) where rooms[i], rooms[j] index a connected pair of self.rooms
        self.main_room_secondary_connections = None

    def _position_rooms(self):

        self.rooms = [rand_room(self.ag, self.rg) for i in range(self.gp.rooms)]

        min_separation = self.gp.room_szmax * self.gp.min_separation_factor

        boids = [Boid(r) for r in self.rooms]

        while True:
            neigbouring_last_pass = 0
            for r in boids:

                neigbours = []
                nearest_neighbour = None
                shortest_dist = self.gp.arena_size * 2

                for other in boids:
                    if r is other:
                        continue

                    d = r.euclidean_dist(other)
                    if d > min_separation:
                        continue

                    if d < shortest_dist:
                        nearest_neighbour = other
                        shortest_dist = d
                    neigbours.append(other)

                if not neigbours:
                    continue

                neigbouring_last_pass += len(neigbours)

                r.separation(
                    nearest_neighbour,
                    min_separation=min_separation,
                    tan_fudge=self.gp.tan_fudge,
                )
                # alignment(r, neigbours)
                # cohesion(r, neigbours)

                r.flock(distance=self.gp.flock_factor)

            if neigbouring_last_pass == 0:
                break

            if self.debug:
                print(
                    f"neigbouring last pass: {neigbouring_last_pass}", file=sys.stderr
                )

            yield neigbouring_last_pass

    def _mark_main_rooms(self):

        w_avg = 0
        l_avg = 0
        for r in self.rooms:
            w_avg += r.width
            l_avg += r.length

        w_avg = w_avg / len(self.rooms)
        l_avg = l_avg / len(self.rooms)
        avg = w_avg * l_avg

        self.imain_rooms = []
        self.isecondary_rooms = []

        thresh = self.gp.main_room_thresh

        for (i, r) in enumerate(self.rooms):
            if r.width * r.length > thresh * avg:
                r.is_main = True
                self.imain_rooms.append(i)
            else:
                self.isecondary_rooms.append(i)

    def _main_rooms_delaunay_triangulation(self):

        self.delaunay_tri_points = np.array(
            [[r.center.x, r.center.y] for r in self.rooms if r.is_main]
        )
        self.delaunay_room_indices = [
            i for (i, r) in enumerate(self.rooms) if r.is_main
        ]

        self.delaunay_mesh = Delaunay(self.delaunay_tri_points)

    def _main_rooms_minimal_spanning_tree(self):
        """
        how to use scipy to generate a minimal spanning tree

        https://notebook.community/tylerjereddy/pycon-2016/computational_geometry_tutorial

        4.4.3 Practical applications of scippy.spatial.Delaunay
        """

        # tri_points are the original room center points
        tri_points = self.delaunay_tri_points
        tris = self.delaunay_mesh
        tri_indices = tris.simplices  # has shape (n_triangles, 3)

        imax = 0
        for tridex in tri_indices:
            for i in tridex:
                if i > imax:
                    imax = i

        uni_graph = np.zeros((imax + 1, imax + 1))

        for tridex in tri_indices:
            equiv_coord_array = tris.points[tridex]
            dist_array = scipy.spatial.distance.pdist(equiv_coord_array)
            uni_graph[tridex[0], tridex[1]] = dist_array[0]
            uni_graph[tridex[0], tridex[2]] = dist_array[1]
            uni_graph[tridex[1], tridex[2]] = dist_array[2]

        for e in np.diag(uni_graph):
            if e != 0.0:
                raise Error(
                    f"diagonal of unidirectional graph should be all zeros: {np.diag(uni_graph)}"
                )

        sparse = scipy.sparse.csgraph.minimum_spanning_tree(uni_graph)
        cx = sparse.tocoo()  # convert to coordinate representation of matrix

        room_points = self.main_room_mst_points = []
        room_connections = self.main_room_mst_connections = dict()
        total_distance = 0

        delaunay_used = dict()

        # each i, j is an edge connecting two main rooms
        for i, j, v in zip(cx.row, cx.col, cx.data):
            if v == 0.0:
                continue
            total_distance += v

            # build an room edge map in terms of indices into self.rooms

            delaunay_used[(i, j)] = True
            delaunay_used[(j, i)] = True

            room_connections[
                (self.delaunay_room_indices[i], self.delaunay_room_indices[j])
            ] = (
                self.delaunay_room_indices[i],
                self.delaunay_room_indices[j],
            )

            # also preserve the raw points for debug rendering
            p1 = tri_points[i]
            p2 = tri_points[j]
            room_points.append(Vec2(p1[0], p1[1]))
            room_points.append(Vec2(p2[0], p2[1]))

        # now add some 'not minimal' edges back in to create less linear structure

        # build a map of currently excluded edges
        excluded_edges = dict()
        for tridex in tri_indices:
            if (tridex[0], tridex[1]) not in delaunay_used:
                excluded_edges[
                    (
                        self.delaunay_room_indices[tridex[0]],
                        self.delaunay_room_indices[tridex[1]],
                    )
                ] = True
            if (tridex[0], tridex[2]) not in delaunay_used:
                excluded_edges[
                    (
                        self.delaunay_room_indices[tridex[0]],
                        self.delaunay_room_indices[tridex[2]],
                    )
                ] = True

        k = int(math.ceil(len(excluded_edges) * (self.gp.corridor_redundancy / 100.0)))

        sample = random.sample([edge for edge in excluded_edges], k=k)

        self.main_room_secondary_connections = sample

        self.room_graph = dict()
        for edge, roompair in sorted(self.main_room_mst_connections.items()):
            self.room_graph[edge] = roompair

        for edge in sorted(self.main_room_secondary_connections):
            self.room_graph[edge] = (edge[0], edge[1])

    def _extrude_corridor(self, i, j, allow_crossing=True):
        """extrude a corridor joining rooms (i, j)"""

        ri = self.rooms[i]
        rj = self.rooms[j]
        bi = Box(ri.topleft(), ri.bottomright())
        bj = Box(rj.topleft(), rj.bottomright())

        hshadow_min = min(ri.width, rj.width) * 0.25
        vshadow_min = min(ri.length, rj.length) * 0.25

        cor = Corridor(joins=[i, j])

        # try plain horzontal corridor
        ok, line, join_sides = g.box_hextrude(bi, bj, min=hshadow_min)
        if ok:
            cor.points = list(line)
            cor.join_sides = list(join_sides)

            # record the index of any crossed room, allong with the wall and corridor segment
            cor.crosses = list(rooms_crossing_line(self.rooms, line, i, j))
            if not cor.crosses or allow_crossing:
                return cor

        # try plain vertical corridor
        ok, line, join_sides = g.box_vextrude(bi, bj, min=vshadow_min)
        if ok:
            cor.points = list(line)
            cor.crosses = list(rooms_crossing_line(self.rooms, line, i, j))
            cor.join_sides = list(join_sides)
            if not cor.crosses or allow_crossing:
                return cor

        # ok, its an elbow. there are always two to pick from. the joins tuple
        # indicates which side the elbow (LEAVES, ENTERS) and is correct for cor.join_sides 'as is'

        (line1, join1), (line2, join2) = g.box_lextrude(
            bi, bj
        )  # each line will be 3 points
        cor.points = list(line1)
        cor.join_sides = list(join1)
        cor.crosses = list(rooms_crossing_line(self.rooms, line1, i, j))

        if not cor.crosses:
            return cor

        cor.alternate = list(line2)
        cor.alternate_join_sides = list(join2)
        cor.alternate_crosses = list(rooms_crossing_line(self.rooms, line2, i, j))

        # if the alternate does not cross, just promote it
        if not cor.alternate_crosses:
            cor.points = list(line2)
            cor.join_sides = list(join2)
            cor.crosses = cor.alternate_crosses
            cor.alternate = ()
            cor.alternate_join_sides = ()
            cor.alternate_crosses = ()

        if allow_crossing:
            return cor

    def _generate_main_corridors(self):

        joined_rooms = self.joined_rooms = dict()
        corridors = self.corridors = []

        for (i, j) in sorted(self.room_graph):

            # Check if we did this corridor from the other direction
            if (j, i) in joined_rooms:
                continue

            cor = self._extrude_corridor(i, j)
            if self.debug and cor is None:
                raise Error(
                    "extrude corridor should always succeede if crossing is allowed"
                )

            icor = len(corridors)
            # room i is the start of the join, j is the end
            self.rooms[i].corridors[cor.join_sides[0]].append(icor)
            self.rooms[j].corridors[cor.join_sides[1]].append(icor)

            joined_rooms[(i, j)] = icor
            corridors.append(cor)

    def _generate_secondary_corridors(self, nconsider=3):
        """go through the non-main (secondary) rooms and join them to the map

        Only, if it can be done without creating more crossing corridors
        """

        # for each secondary room, look through only the nearest N neigbours

        for i in self.isecondary_rooms:
            sr = self.rooms[i]

            ajacency = [(sr.euclidean_dist(self.rooms[j]), j) for j in self.imain_rooms]
            ajacency.sort()
            consider = [j for (_, j) in ajacency[:nconsider]]

            for j in consider:

                if (j, i) in self.joined_rooms:
                    continue
                cor = self._extrude_corridor(i, j)
                if cor is not None:
                    icor = len(self.corridors)
                    # room i is the start of the join, j is the end
                    self.rooms[i].corridors[cor.join_sides[0]].append(icor)
                    self.rooms[j].corridors[cor.join_sides[1]].append(icor)
                    self.joined_rooms[(i, j)] = icor
                    self.corridors.append(cor)
                    break

    def _corridor_lmerge_generate_intersection(self, icor, isegment):
        """ """
        # the other part is the spur we keep
        inter = Room(generation=self.generation)  # intersection
        inter.is_intersection = True
        iinter = len(self.rooms)

        c1 = self.corridors[icor]

        assert isegment == 0 or isegment == 1
        iroom_remove = c1.joins[1 - isegment]
        iroom_keep = c1.joins[isegment]

        # the corridor we just clipped was leaving the room at c1.joins[0] and we just removed that leg
        try:
            side_removed = self.rooms[iroom_remove].detach_corridor(icor)
        except KeyError:
            print(f"{icor} not present (any more) on removal room {iroom_remove}")
            return None, None

        try:
            side_keep = self.rooms[iroom_keep].corridor_side(icor)
        except KeyError:
            print(f"{icor} not present (any more) on keep room {iroom_keep}")
            return None, None

        # the caller is responsible for adding a new corridor to fill the gap between iroom_remove and the new intersection

        # the center for the intersection is always the elbow of the corridor before it is clipped.
        # after clipping its just anoying to pick the right index again
        ip0, ip1, iclipped = None, None, None
        if isegment == 0:
            ip0, ip1, iclipped = 1, 2, 0
        else:
            ip0, ip1, iclipped = 0, 1, 2

        inter.center = c1.points[1]
        clipped_pt = c1.points[iclipped]
        c1.points = [c1.points[ip0], c1.points[ip1]]

        c1.clipped += 1
        c1.joins[isegment] = iroom_keep
        c1.joins[1 - isegment] = iinter
        c1.join_sides[isegment] = c1.join_sides[isegment]
        c1.join_sides[1 - isegment] = RoomSide.opposite(c1.join_sides[isegment])

        icornew = len(self.corridors)

        # if we removed a horizontal leg, we are joining veritcally, otherwise horizontally
        if side_removed in [g.LEFT, g.RIGHT]:
            # is the new room NORTH or SOUTH (-ve y is north) ?
            if inter.center.y < self.rooms[iroom_keep].center.y:
                # the room we are stil attached to is below, so the clipped corridor must
                # enter the new room _from_ bellow thus entering the SOUTH
                inter.corridors[RoomSide.SOUTH].append(icor)
                inter.corridors[RoomSide.opposite(side_removed)].append(icornew)
            else:
                # must be entering the north side then
                inter.corridors[RoomSide.NORTH].append(icor)
                inter.corridors[RoomSide.opposite(side_removed)].append(icornew)
        else:
            assert side_removed in [g.TOP, g.BOTTOM]
            # is the remaining room EAST or WEST ?
            if inter.center.x < self.rooms[iroom_keep].center.x:
                # its WEST so entering from EAST
                inter.corridors[RoomSide.EAST].append(icor)
                inter.corridors[RoomSide.opposite(side_removed)].append(icornew)
            else:
                inter.corridors[RoomSide.WEST].append(icor)
                inter.corridors[RoomSide.opposite(side_removed)].append(icornew)

        self.rooms.append(inter)

        # Now insert a new corridor segment joining iroom_remove to the new intersection.

        # And set the new corridor leg position.
        # this is a little tricky: if j is 0 we are shortening the
        # first leg and so overwrite pt 0 otherwise if j is 1 we are
        # shortening the second leg and overwrite the last pt which
        # is at -1

        # but first save the overwritten point for the new corror - which will be a 2 point flat
        cornew = Corridor(
            points=[Vec2(), Vec2()], is_inserted=True, generation=self.generation
        )
        cornew.points[0] = clipped_pt
        cornew.points[1] = inter.center.clone()

        # iroom_removed is the room index we orphaned. side is the side of that room
        # c1 was attached to before it was clipped
        cornew.joins = [iroom_remove, iinter]
        cornew.join_sides = [side_removed, RoomSide.opposite(side_removed)]

        self.corridors.append(cornew)
        self.rooms[iroom_remove].corridors[side_removed].append(icornew)

        return iinter, icornew

    def _corridor_lmerge_even(self, icor, jcor, iside, jside):
        """Produce 1 new corridor segment and  an intersection.

        The original corridors are clipped and attached to the new intersection.

        All involved corridors will be horizontal or vertical (2 pt) sections on return

        iside = jside == 0
                + j2
                |   <- spur a
        j0+-----+ j1
        i0+-----+ i1
                | <- spur b
                + i2

        """
        raise NotImplementedError()

    def _corridor_lmerge_spur(self, icor, jcor, iside, jside):
        """Produce 1 new corridor segment and an intersection.

        The original corridors are clipped and attached to the new intersection.

        One of the existing corridors is redunced from an L to a Straight

        The caller must ensure that icor has the 'long' side


        iside = jside == 0
                  + i2
                  |
        i0+-------+ i1
        j0+----+ j1
               | <- spur
               + j2

        +----+
             |
             +---+ <- spur
             |
             +

        """

        inter = Room(generation=self.generation)  # intersection
        inter.is_intersection = True

        cornew = Corridor(
            points=[Vec2(), Vec2()], is_inserted=True, generation=self.generation
        )
        iinter = len(self.rooms)
        icornew = len(self.corridors)

        ci, cj = self.corridors[icor], self.corridors[jcor]
        ci_join_sides_orig = ci.join_sides[:]

        # the intersection position is th
        inter.center = cj.points[1].clone()

        # 1. remove the long leg from the entangled room and attach it to
        # the new interesection.

        # iside is the 'long' side. remove it from its current room
        # note that iside also indexs the join and join_sides ends
        iroom_remove = ci.joins[iside]
        iside_removed = self.rooms[iroom_remove].detach_corridor(icor)

        # attach the new intersection to the original corridor ci
        # inter.corridors[iside].append(icor)  # room -> corridor
        # inter.corridors[RoomSide.opposite(iside_removed)].append(icor)  # room -> corridor
        inter.corridors[iside_removed].append(icor)  # room -> corridor

        # attach the the original corridor ci to the new intersection
        ci.joins[iside] = iinter  # corridor -> room
        # ci.join_sides doesn't change
        ci_orig_points = ci.points[:]
        ci.points[0 if iside == 0 else 2] = inter.center.clone()
        ci.clipped =True

        # end 1. ci is now completely detatched from the original room and
        # instead attached to the new intersection.

        # 2. remove the short leg of cj and attach it to the intesection. converting it
        # from an L to a Straight
        if jside == 0:
            # keeping side 1
            cj.points = cj.points[1:]
        else:
            # keeping side 0
            cj.points = cj.points[0:2]
        cj.clipped = True

        # attach the corridor to the new intersection
        cj.joins[jside] = iinter

        # The join_sides is a little trickier this time. its the *opposite*
        # side of the un-changed end
        cj_join_sides_orig = cj.join_sides[:]
        cj.join_sides[jside] = RoomSide.opposite(cj.join_sides[1 - jside])
        # and the intersection needs to be connected to the un-changed end of the spur
        inter.corridors[cj.join_sides[jside]].append(jcor)

        # attach the new corridor to the clipped short leg. Note that
        # this attachment is awkward - its at 90'

        if cj_join_sides_orig[1-jside] in [RoomSide.NORTH, RoomSide.SOUTH]:

            # the side of cj we are keeping runs north-south so we are attaching on the west or east
            # the side of cj we are keeping runs north-south so we are attaching on the west or east
            # assert ci.join_sides[1-iside] in [RoomSide.NORTH, RoomSide.SOUTH]
            # assert ci.join_sides[iside] in [RoomSide.WEST, RoomSide.EAST]

            # cj runs north-south so we are attaching on the west east
            if ci.join_sides[iside] == RoomSide.WEST:
                inter.corridors[RoomSide.EAST].append(icornew)
                #assert RoomSide.opposite(ci.join_sides[iside]) == RoomSide.EAST
            else:
                inter.corridors[RoomSide.WEST].append(icornew)
                #assert RoomSide.opposite(ci.join_sides[iside]) == RoomSide.WEST

        else:
            # the side of cj we are keeping runs west-east so we are attaching on the north or south
            #assert ci.join_sides[1-iside] in [RoomSide.WEST, RoomSide.EAST]
            #assert ci.join_sides[iside] in [RoomSide.NORTH, RoomSide.SOUTH]

            if ci.join_sides[iside] == RoomSide.NORTH:
                # The side we are keeping enters the north side of the other room, 
                # the corridor must be leaving the south of the intersection
                inter.corridors[RoomSide.SOUTH].append(icornew)
                #assert RoomSide.opposite(ci.join_sides[iside]) == RoomSide.SOUTH
            else:
                inter.corridors[RoomSide.NORTH].append(icornew)
                #assert RoomSide.opposite(ci.join_sides[iside]) == RoomSide.NORTH

        # end 2. cj is completely detached from the original room and
        # instead attached to the new interesection.

        # At this point iroom_removed is completely detatched from the
        # original entangled corridors. Now we re-attach it to the new
        # intersection using the new corridor.

        ci.entangled.remove(jcor)
        cj.entangled.remove(icor)

        # 3. build the new corridor and attach it to the room we just removed from ci, cj

        # select the points for the new corridor

        # the clipped point is one of the end points for the new corridor
        iclipped_pt = 0 if iside == 0 else 2
        cliped_pt = ci_orig_points[iclipped_pt].clone()
        cornew.points[iside] = cliped_pt

        # the other point for the new corridor is intersection, which was
        # taken from the mid point of the short leg.
        cornew.points[1 - iside] = inter.center.clone()  # == cj.points[1].clone()

        # attach the new corridor to the room we removed from ci. it enters
        # the same side as it must be the same direction
        cornew.joins = [None, None]
        cornew.join_sides = [None, None]
        cornew.joins[iside] = iroom_remove
        cornew.join_sides[iside] = iside_removed
        cornew.joins[1 - iside] = iinter
        cornew.join_sides[1 - iside] = RoomSide.opposite(iside_removed)

        # attach the room we removed from ci to the new corridor, attach it back to the same side
        self.rooms[iroom_remove].corridors[iside_removed].append(icornew)

        self.rooms.append(inter)
        self.corridors.append(cornew)

    def _corridor_lmerge(self, icor, jcor):
        """

        strategy: find the 'short' L spur and insert a new room at that point.
        mark the room as an intersection so we can handle it (in the
        content/game layer) distinctly from actual rooms


        L,L staggered

                +1
                |
        0+------+
            |    <-- spur
            +1

        L,L even
                +1
                | <- spur a
        0+------+
                | <- spur b (can pick either)
                +1

        """

        # if its the even case pick c
        ci = self.corridors[icor]
        cj = self.corridors[jcor]

        if len(ci.points) != 3 and len(cj.points) != 3:
            raise ValueError("corridor_lmerge requires two elbows")

        for i in range(2):
            ci_a, ci_b = ci.points[i], ci.points[i + 1]
            for j in range(2):

                # if it gets clipped on the previous pass, we need to skip it
                if len(cj.points) != 3:
                    continue

                cj_a, cj_b = cj.points[j], cj.points[j + 1]

                # for the entangled_even case we still need to pick the right sides
                if g.check_line_in_line(cj_a, cj_b, ci_a, ci_b):
                    # c2 in c1 so c1 is long
                    assert not (ci.entangled_even or cj.entangled_even)
                    self._corridor_lmerge_spur(icor, jcor, i, j)
                    return

                elif g.check_line_in_line(ci_a, ci_b, cj_a, cj_b):
                    assert not (ci.entangled_even or cj.entangled_even)
                    self._corridor_lmerge_spur(jcor, icor, j, i)
                    return

                elif g.pt_essentially_same(ci_a, cj_a) and g.pt_essentially_same(ci_b, cj_b):
                    assert ci.entangled_even or cj.entangled_even
                    self._corridor_lmerge_even(icor, jcor, i, j)
                    return

    def _generate_corridor_intersections(self):
        """resolve overlapping or crossing corridors"""

        #room_crossing = [cor for cor in self.corridors if cor.crosses]
        #if not room_crossing:
        #    print("no corridors are corssing rooms")
        #else:
        #    print(f"{len(room_crossing)} corridors are crossing rooms")

        for i, r in enumerate(self.rooms):

            # as we add corridors and rooms as we go, we guard against re-processing
            if r.is_intersection:
                continue

            if r.generation == self.generation:
                # if we just created it, leave it till next pass
                print(f"skipping new room {i}")
                continue

            for side in range(4):
                side_corridors = set(r.corridors[side])
                if len(side_corridors) <= 1:
                    continue

                # for each pair m, n of corridors see if they are actually
                # co-incident due to how we make corridors, we only need to
                # find a single end point to confirm the entanglement.
                for ic in side_corridors:
                    for jc in side_corridors:
                        if ic == jc:
                            continue

                        for pti in self.corridors[ic].points:
                            for ptj in self.corridors[jc].points:
                                if g.pt_essentially_same(pti, ptj):
                                    self.corridors[ic].entangle(jc)
                                    self.corridors[jc].entangle(ic)
                                    if pti == ptj and pti == 1:
                                        self.corridors[ic].entangled_even = True
                                        self.corridors[jc].entangled_even = True

            considered = set([])
            for ic, c in enumerate(self.corridors):
                if not c.entangled:
                    continue
                if c.generation == self.generation:
                    print(f"skipping new corridor {ic}")
                for jc in list(c.entangled or []):
                    if (ic, jc) in considered or (jc, ic) in considered:
                        continue
                    c1, c2 = self.corridors[ic], self.corridors[jc]
                    if c2.generation == self.generation:
                        print(f"skipping new entangled corridor {jc}")
                        continue
                    if len(c1.points) == 3 and len(c2.points) == 3:
                        self._corridor_lmerge(ic, jc)
                    considered.add((ic, jc))
                    considered.add((jc, ic))

    def generate(self, map):

        self._reset_generator(map.gp)

        for x in self._position_rooms():
            yield x

        # If the map is saved after generation, we save this state so
        # we re-build faithfully on load
        self._rng_load_state = map.get_rng_state()

        self.generation = 0

        self._mark_main_rooms()
        self._main_rooms_delaunay_triangulation()
        self._main_rooms_minimal_spanning_tree()
        self._generate_main_corridors()
        self._generate_secondary_corridors()

        self.generation = 1
        self._generate_corridor_intersections()

        self._generated = True

    def fromjson(self, map, model):
        """load the model

        NOTE: this will reset the rng state"""

        self._reset_generator(map.gp)

        self.rooms = []
        for r in model["rooms"]:
            c = Vec2(r["x"], r["y"])
            self.rooms.append(Room(c, r["w"], r["l"]))

        if "rng_state" in model:
            self._rng_load_state = model["rng_state"]
            map.set_rng_state(self._rng_load_state)
        else:
            self._rng_load_state = map.get_rng_state()

        self.generation = 0

        self._mark_main_rooms()
        self._main_rooms_delaunay_triangulation()
        self._main_rooms_minimal_spanning_tree()
        self._generate_main_corridors()
        self._generate_secondary_corridors()

        self.generation = 1
        self._generate_corridor_intersections()

        self._loaded = True

    def tojson(self, dumps=False):
        """save the generated model to json compatible object tree"""

        rooms = []
        for r in self.rooms:
            rooms.append(
                dict(
                    x=r.center.x, y=r.center.y, w=r.width, l=r.length,
                    is_main=r.is_main,
                    corridors=r.corridors
                    ))

        corridors = []
        for c in self.corridors:
            corridors.append(
                dict(points=[[p.x, p.y] for p in c.points], joins=c.joins, join_sides=c.join_sides)
            )

        model = dict(rng_state=self._rng_load_state, rooms=rooms, corridors=corridors)
        if not dumps:
            return model

        return json.dumps(model, sort_keys=True, indent=2)

    def create_render_opts(self, args):
        """create a default render opts. args is assumed to contain at least the defaults for map:Map"""
        opts = RenderOpts()
        opts.label_rooms = not args.no_label_rooms
        opts.label_corridors = not args.no_label_corridors
        opts.legend = not args.no_legend
        return opts

    def render(self, dwg, arena, opts=None):

        # if not (self._generated or self._loaded):
        #     raise Error("you must generate or load a model before rendering")

        Viewer(self).render(self.gp, dwg, arena, opts=opts)
