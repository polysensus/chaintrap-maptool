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
from maptool.generators.tinykeep.intersections import GenerateIntersections
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

    def __init__(self, debug=False, allow_crossing=False):
        self.debug = debug
        self.debug_room_graph = False
        self.allow_crossing = allow_crossing

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

    def _extrude_corridor(self, i, j):
        """extrude a corridor joining rooms (i, j)"""

        ri = self.rooms[i]
        rj = self.rooms[j]
        bi = Box(ri.topleft(), ri.bottomright())
        bj = Box(rj.topleft(), rj.bottomright())

        if bi.tl.x > bj.tl.x:
            i, j = j, i
            ri, rj = rj, ri
            bi, bj = bj, bi

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
            if not cor.crosses or self.allow_crossing:
                return cor, i, j

        # try plain vertical corridor
        ok, line, join_sides = g.box_vextrude(bi, bj, min=vshadow_min)
        if ok:
            cor.points = list(line)
            cor.crosses = list(rooms_crossing_line(self.rooms, line, i, j))
            cor.join_sides = list(join_sides)
            if not cor.crosses or self.allow_crossing:
                return cor, i, j

        # ok, its an elbow. there are always two to pick from. the joins tuple
        # indicates which side the elbow (LEAVES, ENTERS) and is correct for cor.join_sides 'as is'

        print(f"extrude: r{i}, r{j}")

         # each line will be 3 points
        (line1, join1), (line2, join2) = g.box_lextrude( bi, bj)
        cor.points = list(line1)
        cor.join_sides = list(join1)
        cor.crosses = list(rooms_crossing_line(self.rooms, line1, i, j))

        if not cor.crosses:
            return cor, i, j

        cor.alternate = list(line2)
        cor.alternate_join_sides = list(join2)
        cor.alternate_crosses = list(rooms_crossing_line(self.rooms, line2, i, j))

        # if the alternate does not cross, just promote it
        if not cor.alternate_crosses:
            cor.points = list(line2)
            cor.crosses = cor.alternate_crosses
            cor.join_sides = cor.alternate_join_sides
            cor.alternate = ()
            cor.alternate_join_sides = ()
            cor.alternate_crosses = ()

        if self.allow_crossing:
            return cor, i, j

    def _generate_main_corridors(self):

        joined_rooms = self.joined_rooms = dict()
        corridors = self.corridors = []

        for (i, j) in sorted(self.room_graph):

            # Check if we did this corridor from the other direction
            if (j, i) in joined_rooms:
                continue

            cor = self._extrude_corridor(i, j)
            if self.debug and self.allow_crossing and cor is None:
                raise Error(
                    "extrude corridor should always succeede if crossing is allowed"
                )
            if cor is None:
                print(f"cant join rooms {i}, {j} without a crossing")
                continue

            cor, i, j = cor

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
                if cor is None:
                    continue

                cor, i, j = cor
                icor = len(self.corridors)
                # room i is the start of the join, j is the end
                self.rooms[i].corridors[cor.join_sides[0]].append(icor)
                self.rooms[j].corridors[cor.join_sides[1]].append(icor)
                self.joined_rooms[(i, j)] = icor
                self.corridors.append(cor)
                break


    def _generate_intersections(self):

        gi = GenerateIntersections(self.rooms, self.corridors)
        entangled = gi.find_first_entangled_corridor_pair()
        while entangled:
            ic, jc = entangled
            ok = gi.generate_corridor_intersection(ic, jc)
            assert ok
            entangled = gi.find_first_entangled_corridor_pair()


    def _generate_corridors(self, map):

        self._mark_main_rooms()
        self._main_rooms_delaunay_triangulation()
        self._main_rooms_minimal_spanning_tree()
        self._generate_main_corridors()

        opts = self.create_render_opts(map.args)
        self._generate_secondary_corridors()

        import svgwrite
        dwg = svgwrite.Drawing(filename="x-pre.svg")
        arena = dwg.add(dwg.g(id="arena", fill="blue"))
        self.render(dwg, arena, opts=opts)
        dwg.save(pretty=True)

        self._generate_intersections()


    def generate_rooms(self, map):

        self._reset_generator(map.gp)
        list(self._position_rooms())


    def generate_corridors(self, map):
        self._generate_corridors(map)


    def generate(self, map):

        self.generate_rooms(map)
        self.generate_corridors(map)
        self._generated = True

    def load_rooms(self, map, model):
        """load the model rooms"""

        self.rooms = []

        for r in model["rooms"]:
            self.rooms.append(Room.from_encoding(r))

    def load_corridors(self, map, model):
        self.corridors = []

        for c in model["corridors"]:
            self.corridors.append(Corridor.from_encoding(c))


    def fromjson(self, map, model):
        """load the model"""

        self._reset_generator(map.gp)
        self.load_rooms(map, model)
        self.load_corridors(map, model)
        self._loaded = True

    def tojson(self, dumps=False):
        """save the generated model to json compatible object tree"""

        rooms = []
        for r in self.rooms:
            rooms.append(r.encode())

        corridors = []
        for c in self.corridors:
            corridors.append(c.encode())

        model = dict(rooms=rooms, corridors=corridors)
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
