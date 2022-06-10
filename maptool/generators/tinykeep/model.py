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

        print(f"extrude: r{i}, r{j}")

        ifoot, (line1, join1), (line2, join2) = g.box_lextrude(
            bi, bj
        )  # each line will be 3 points
        cor.points = list(line1)
        cor.join_sides = list(join1)

        cor.joins[0], cor.joins[1] = cor.joins[ifoot], cor.joins[1-ifoot]

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

        # if it gets clipped on the previous pass, we need to skip it
        if len(ci.points) != 3 or len(cj.points) != 3:
            return

        if ci.joins[0] == cj.joins[0]:
            if (g.dist2(cj.points[0], cj.points[0]) < g.dist2(ci.points[0], ci.points[1])):

                iri = self._corridor_lmerge_split_long(icor, 0, cj.points[1].clone())
                self._corridor_lmerge_truncate_short(jcor, 0, iri)
            else:
                iri = self._corridor_lmerge_split_long(jcor, 0, ci.points[1].clone())
                self._corridor_lmerge_truncate_short(icor, 0, iri)
        elif ci.joins[0] == cj.joins[1]:
            if (g.dist2(cj.points[1], cj.points[2]) < g.dist2(ci.points[0], ci.points[1])):
                iri = self._corridor_lmerge_split_long(icor, 0, cj.points[1].clone())
                self._corridor_lmerge_truncate_short(jcor, 1, iri)
            else:
                iri = self._corridor_lmerge_split_long(jcor, 0, ci.points[1].clone())
                self._corridor_lmerge_truncate_short(icor, 1, iri)

        elif ci.joins[1] == cj.joins[0]:
            if (g.dist2(cj.points[0], cj.points[0]) < g.dist2(ci.points[1], ci.points[2])):
                iri = self._corridor_lmerge_split_long(icor, 1, cj.points[1].clone())
                self._corridor_lmerge_truncate_short(jcor, 0, iri)

            else:
                iri = self._corridor_lmerge_split_long(jcor, 0, ci.points[1].clone())
                self._corridor_lmerge_truncate_short(icor, 1, iri)

        else:
            assert ci.joins[1] == cj.joins[1]
            if (g.dist2(cj.points[1], cj.points[2]) < g.dist2(ci.points[1], ci.points[2])):
                # lmerge_spur[(1,1)](icor, jcor)
                iri = self._corridor_lmerge_split_long(icor, 1, cj.points[1].clone())
                self._corridor_lmerge_truncate_short(jcor, 1, iri)

            else:
                # lmerge_spur[(1,1)](jcor, icor)
                iri = self._corridor_lmerge_split_long(jcor, 1, ci.points[1].clone())
                self._corridor_lmerge_truncate_short(icor, 1, iri)

        self.corridors[icor].entangled.remove(jcor)
        self.corridors[jcor].entangled.remove(icor)


    def _corridor_lmerge_split_long(self, icor, r1end, pi):
        """
        Here we are spliting the L between R1 - R2 on the leg joining R1 and inserting a new straight corridor segment
        to join the new intersection to R1

                   R2
            RI(pi) | ci
        R1 --+-----+ r1end=0
             |
               R1 r1end=1
                |
          RI(pi)+--
             ci |
        R2 -----+
        """

        ci = self.corridors[icor]

        # the corridor foot rests on the room attached to the side we are splitting
        ipfoot = r1end * 2 # 0 or 2

        # the corridor head rests on the room attached to the side we are not splitting
        iphead = (1-r1end) * 2 # 0 or 2


        # Make a new corridor joining R1 to the intersection point. The
        # intersection point is the elbow point of the shorter leg of cj.
        ir1 = ci.joins[r1end]
        r1 = self.rooms[ir1]

        # The foot of the new corridor will rest on r1
        p1 = ci.points[ipfoot].clone()

        # create the new corridor segment and the intersection
        cn = Corridor(
            points=[None, None],
            joins=[None, None],
            join_sides=[None, None],
            is_inserted=True, generation=self.generation
        )

        # note: use r1end directly as cn is a straight with 2 points
        cn.points[r1end] = p1 # R1
        cn.points[1- r1end] = pi # RI

        ri = Room(generation=self.generation)  # intersection
        ri.is_intersection = True
        ri.center = pi.clone()

        # The new intersection room index
        iri = len(self.rooms)
        ici = len(self.corridors)

        self.corridors.append(cn)
        self.rooms.append(ri)

        # detach ci from room 1 and clip it

        # set the foot of the second leg to the intersection position
        ci.points[ipfoot] = pi.clone()
        ci.clipped += 1 

        # detach ci from room 1
        r1iside = r1.detach_corridor(icor)

        # attach it to the intersection the side of attachment is the *same*
        # side as it was previously attached to R1 on.
        ri.corridors[r1iside].append(icor)

        # update the join for the clipped end so it joins to the new intersection
        orig = ci.joins[:]
        orig_sides = ci.join_sides[:]
        assert ci.joins[r1end] == ir1
        ci.joins[r1end] = iri

        print(f"split-long: cor: {icor} ci: {str(ci.joins)} -> {ci.joins}. joins")    

        # make the new corridor segment have the same direction, towards R1, as
        # did ci's leg that we split.

        orig = cn.joins[:] # so we can log before and after
        cn.joins[r1end] = ir1 # R1
        cn.joins[1 - r1end] = iri # intersection
        cn.join_sides[r1end] = r1iside
        cn.join_sides[1 - r1end] = RoomSide.opposite(r1iside)
        r1.corridors[cn.join_sides[r1end]].append(ici)
        ri.corridors[cn.join_sides[1 - r1end]].append(ici)

        print(f"split-long: cor: {icor} cn: {str(orig)} -> {str(cn.joins)}. joins")
        print(f"split-long: cor: {icor} cn: {str(orig_sides)} -> {str(cn.join_sides)}. join_sides")
        print(f"split-long: cor: {icor} cn: {str(r1.corridors)}. r[{ir1}].corridors")
        print(f"split-long: cor: {icor} cn: {str(ri.corridors)}. r[{iri}].corridors")

        return iri


    def _corridor_lmerge_truncate_short(self, icor, r1end, iri):
        """
        Here we are making the L between R1 - R3 into a straight joining R1 R3

        We do this by removing the r1end point. The old elbow point becomes the end point. Which is also the center of the new intersection

 r1end=0           
            RI(pi) |
        R1 --+-----+ 
             |  ci
             R3 

               R1 r1end=1
                |     ci
          RI(pi)+----R3 
                |
           -----+
       
        """
        ci = self.corridors[icor]
        r1 = self.rooms[ci.joins[r1end]]
        r3 = self.rooms[ci.joins[1 - r1end]]

        # adjust the corridor join to end at the RI intersection rather than R1
        orig = ci.joins[:]
        orig_sides = ci.join_sides[:]

        # we are removing the leg of the elbow that rests on the common room r1
        if r1end == 0:
            ci.points = ci.points[1:]
        else:
            ci.points = ci.points[:2]
        ci.clipped += 1 

        # we want the side *opposite* the side we attach too on R3    
        riside = RoomSide.opposite(ci.join_sides[1-r1end])

        # note: iri is a parameter as it is typically generated by spliting the other entangled 'longer' corridor segment.
        ci.joins[r1end] = iri
        ci.join_sides[r1end] = riside

        print(f"trunc-short: cor: {icor}, ci: {str(orig)} -> {str(ci.joins)}. joins")
        print(f"trunc-short: cor: {icor} ci: {str(orig_sides)} -> {str(ci.join_sides)}. join_sides")

        # detach from R1
        r1.detach_corridor(icor)

        # the re-attachment has to be derived from room 3. we want the opposite of the side icor is attached to.
        riside = RoomSide.opposite(r3.attached_side(icor))
        # attach the truncated corridor to the intersection
        ri = self.rooms[iri]
        ri.corridors[riside].append(icor)
        ir1 = orig[r1end]
        print(f"trunc-short: cor: {icor} cn: {str(r1.corridors)}. r[{ir1}].corridors")
        print(f"trunc-short: cor: {icor} cn: {str(ri.corridors)}. r[{iri}].corridors")


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

                    considered.add((ic, jc))
                    # considered.add((jc, ic))
                    if len(c1.points) == 3 and len(c2.points) == 3:
                        self._corridor_lmerge(ic, jc)
                        continue
                    if len(c1.points) == 2 and len(c2.points) == 3:
                        self._corridor_hvlmerge(ic, jc)
                        continue
                    if len(c1.points) == 3 and len(c2.points) == 2:
                        self._corridor_hvlmerge(ic, jc)
                        continue


    def _generate_corridors(self):

        self.generation = 0

        self._mark_main_rooms()
        self._main_rooms_delaunay_triangulation()
        self._main_rooms_minimal_spanning_tree()
        self._generate_main_corridors()
        self._generate_secondary_corridors()

        self.generation = 1

        nc, nr = len(self.corridors), len(self.rooms)
        self._generate_corridor_intersections()

        return
        while nc != len(self.corridors) or nr != len(self.rooms):
            self.generation += 1
            nc, nr = len(self.corridors), len(self.rooms)
            self._generate_corridor_intersections()

    def generate(self, map):

        self._reset_generator(map.gp)

        for x in self._position_rooms():
            yield x

        # If the map is saved after generation, we save this state so
        # we re-build faithfully on load
        self._rng_load_state = map.get_rng_state()

        self._generate_corridors()
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

        self._generate_corridors()

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
