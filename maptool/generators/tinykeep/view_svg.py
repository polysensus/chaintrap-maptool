from typing import Dict
from dataclasses import dataclass, field
from numpy import append
from svgwrite import mm
from svgwrite.mixins import ViewBox

from maptool.datatypes import Vec2
from maptool.room import rooms_bbox, SIDES, RoomSide


@dataclass
class SceneItem:
    fill: str = "black"
    stroke: str = "black"
    stroke_width: int = 3
    class_: str = ""
    attribs: dict = None


@dataclass
class SceneLine(SceneItem):
    start: Vec2 = field(default_factory=Vec2)
    end: Vec2 = field(default_factory=Vec2)


@dataclass
class SceneCircle(SceneItem):
    center: Vec2 = field(default_factory=Vec2)
    r: float = 0.0
    opacity: float = 1.0


@dataclass
class SceneText(SceneItem):
    insert: Vec2 = field(default_factory=Vec2)
    text: str = ""
    font_size: int = 14
    font_family: str = "monospace"
    font_weight: str = "normal"


@dataclass
class SceneRect(SceneItem):
    insert: Vec2 = field(default_factory=Vec2)
    size: Vec2 = 5.0


@dataclass
class ScenePolyline(SceneItem):
    points: list = ()

    def __init__(self, points=None, **kw):
        super().__init__(**kw)
        self.points = points


@dataclass
class ScenePoly(SceneItem):
    points: list = ()

    def __init__(self, points=None, **kw):
        super().__init__(**kw)
        self.points = points


@dataclass
class RenderOpts:
    gp: Dict = None
    scale: float = 1.0 / 25.0
    corridor_end_size: float = 120.0
    grid: float = 3

    label_colour: str = "yellow"
    label_font_size: float = 15
    label_size: float = 300

    label_rooms: bool = True

    label_corridors: bool = True
    label_corridors_font_size: float = 11
    label_corridors_size: float = 200

    legend: bool = True
    legend_font_size: float = 20


class Viewer:
    def __init__(self, model):
        self.model = model

    def add_markers(self, dwg):
        # markers from  https://raw.githubusercontent.com/mozman/svgwrite/master/examples/marker.py
        # 'insert' represents the insertation point in user coordinate space
        # in this example its the midpoint of the circle, see below
        marker_start = dwg.marker(
            insert=(0, 0), size=(5, 5)
        )  # target size of the marker
        # setting a user coordinate space for the appanded graphic elements
        # bounding coordinates for this example:
        # minx = -5, maxx = +5, miny = -5, maxy = +5
        marker_start.viewbox(
            minx=-5, miny=-5, width=10, height=10
        )  # the marker user coordinate space
        marker_start.add(dwg.circle((0, 0), r=5)).fill("red", opacity=0.5)

        # --end-- A blue point as marker-end element
        # a shorter form of the code above:
        marker_end = dwg.marker(size=(5, 5))  # marker defaults: insert=(0,0)
        # set viewbox to the bounding coordinates of the circle
        marker_end.viewbox(-1, -1, 2, 2)
        marker_end.add(
            dwg.circle(fill="blue", fill_opacity=0.5)
        )  # circle defaults: insert=(0,0), r=1

        # --mid-- A green point as marker-mid element
        # if you don't setup a user coordinate space, the default ucs is
        # minx = 0, miny = 0, maxx=size[0], maxy=size[1]
        # default size = (3, 3) defined by the SVG standard
        # bounding coordinates for this example:
        # minx = 0, maxx = 6, miny = 0, maxy = 6
        # => center of the viewbox = (3, 3)!
        marker_mid = dwg.marker(insert=(3, 3), size=(6, 6))
        marker_mid.add(dwg.circle((3, 3), r=3)).fill("green", opacity=0.7)

        # The drawing size of the 'start-marker' is greater than the drawing size of
        # the 'marker-mid' (r=5 > r=3), but the resulting size is defined by the
        # 'size' parameter of the marker object (size=(6,6) > size=(5,5)), so the
        # 'marker-start' is smaller than the 'marker-mid'.

        # add marker to defs section of the drawing
        dwg.defs.add(marker_start)
        dwg.defs.add(marker_mid)
        dwg.defs.add(marker_end)

    def add_grid(self, layer, bbox, opts: RenderOpts):

        opacity_step = 1.0 / opts.grid

        w, h = bbox.width_height()

        grid_step = Vec2(w / opts.grid, h / opts.grid)

        # vertical lines
        opacity = 0.0
        p1 = bbox.tl.clone()
        p2 = Vec2(bbox.tl.x, bbox.br.y)

        for i in range(int(opts.grid) + 1):

            layer.append(
                SceneLine(
                    start=p1.clone(),
                    end=p2.clone(),
                    stroke="blue",
                    stroke_width=1,
                    attribs=dict(opacity=opacity if i != 0 else 1.0),
                )
            )
            opacity = opacity + opacity_step
            if opacity > 1.0:
                opacity = 1.0
            p1.x += grid_step.x
            p2.x += grid_step.x

        # horizontal lines
        opacity = 0.0
        p1 = bbox.tl.clone()
        p2 = Vec2(bbox.br.x, bbox.tl.y)

        for i in range(int(opts.grid) + 1):
            layer.append(
                SceneLine(
                    start=p1.clone(),
                    end=p2.clone(),
                    stroke="blue",
                    stroke_width=1,
                    attribs=dict(opacity=opacity if i != 0 else 1.0),
                )
            )
            opacity = opacity + opacity_step
            if opacity > 1.0:
                opacity = 1.0

            p1.y += grid_step.y
            p2.y += grid_step.y

    def add_construction_elements(self, layer, opts: RenderOpts):

        if self.model.debug_room_graph:

            if self.model.room_mst_connections is not None:
                for (i, j) in self.model.room_mst_connections:
                    p1 = self.model.rooms[i].center
                    p2 = self.model.rooms[j].center

                    layer.append(
                        SceneLine(start=p1, end=p2, stroke="green", stroke_width=3)
                    )

            if self.model.room_secondary_connections is not None:

                for (i, j) in self.model.room_secondary_connections:
                    p1 = self.model.rooms[i].center
                    p2 = self.model.rooms[j].center
                    layer.append(
                        SceneLine(start=p1, end=p2, stroke="blue", stroke_width=1)
                    )

            if not self.model.debug_room_graph and self.model.room_graph is not None:
                for (i, j) in self.model.room_graph:
                    p1 = self.model.rooms[i].center
                    p2 = self.model.rooms[j].center
                    layer.append(
                        SceneLine(start=p1, end=p2, stroke="blue", stroke_width=5)
                    )

        if self.model.delaunay_tri_points is not None:

            for poly_points in self.model.delaunay_tri_points[
                self.model.delaunay_mesh.simplices
            ]:
                points = []
                for pt in poly_points:
                    points.append(Vec2(pt[0], pt[1]))
                layer.append(
                    ScenePoly(
                        points=points,
                        fill="none",
                        stroke="grey",
                        stroke_width=1,
                        attribs=dict(opacity=0.1),
                    )
                )

    def add_label(
        self,
        layer,
        center,
        text,
        opts: RenderOpts,
        font_size=None,
        label_size=None,
        colour=None,
    ):

        if colour is None:
            colour = opts.label_colour

        if label_size is None:
            label_size = opts.label_size

        if font_size is None:
            font_size = opts.label_font_size

        layer.append(
            SceneCircle(center=center, r=label_size, fill=colour, stroke_width=1)
        )

        dx = -(max(len(text) - 1, 0) / 2.0) * opts.label_size
        dx = -(len(text) / 3.0) * opts.label_size

        insert = Vec2(center.x + dx, center.y + opts.label_size / 2.5)

        layer.append(
            SceneText(insert=insert, text=text, font_size=font_size, stroke_width=0.5)
        )

    def add_corridor_label(self, layer, center, text, opts: RenderOpts, colour=None):
        return self.add_label(
            layer,
            center,
            text,
            opts,
            colour=colour,
            font_size=opts.label_corridors_font_size,
            label_size=opts.label_corridors_size,
        )

    def add_legend_entry(self, layer, legend_line_start, opts, fmt, **kw):

        layer.append(
            SceneText(
                insert=legend_line_start.clone(),
                text=fmt.format(**kw),
                stroke_width=0.5,
            )
        )
        legend_line_start.y += opts.label_size * 1.5

    def build_scene(self, bbox, gp, opts: RenderOpts):

        layers = []

        layers.append([])
        ground = layers[-1]
        ground.append(
            SceneCircle(
                center=Vec2(0.0, 0.0),
                r=gp.arena_size,
                fill="none",
                stroke="blue",
                stroke_width=1,
                attribs=dict(stroke_opacity=0.2),
            )
        )

        if opts.grid is not None:
            self.add_grid(ground, bbox, opts)

        layers.append([])
        self.add_construction_elements(layers[-1], opts)

        structure = []
        layers.append(structure)
        labels = []
        layers.append(labels)
        legend = []
        layers.append(legend)

        legend_line_start = [
            Vec2(bbox.tl.x, bbox.br.y + opts.label_size),
            Vec2(bbox.br.x, bbox.br.y + opts.label_size),
        ]

        def add_legend_entry(fmt, **kw):
            if not opts.legend:
                return
            line_start = legend_line_start[kw.pop("col", 0)]
            self.add_legend_entry(legend, line_start, opts, fmt, **kw)

        add_legend_entry("Rooms")
        add_legend_entry("Corridors", col=1)

        def add_room_legend(i):

            r = self.model.rooms[i]

            kind = "inter"
            if not r.is_intersection:
                kind = "room"

            north = f"{','.join(map(str, r.corridors[RoomSide.NORTH]))}"
            west = f"{','.join(map(str, r.corridors[RoomSide.WEST]))}"
            south = f"{','.join(map(str, r.corridors[RoomSide.SOUTH]))}"
            east = f"{','.join(map(str, r.corridors[RoomSide.EAST]))}"
            add_legend_entry(
                f"{kind} ({i}): corridors N={north}, W={west}, S={south}, E={east}",
                col=0,
            )

        def add_corridor_legend(i):

            c = self.model.corridors[i]

            axis = "degenerate"
            joins = "-"
            if c.join_sides:
                axis = (
                    f"{RoomSide.name(c.join_sides[0])}-{RoomSide.name(c.join_sides[1])}"
                )
                joins = f"{c.joins[0]}.{c.joins[1]}"

            kind = "linear"
            if len(c.points) == 3:
                kind = "elbow"

            entangled = f"{','.join(map(str, list(c.entangled)))}"
            add_legend_entry(
                f"cor ({i}): kind={kind}, {axis}, joins={joins},{' inserted,' if c.is_inserted else ' '}clipped={c.clipped}, entangled={entangled}",
                col=1,
            )

        for i, r in enumerate(self.model.rooms):

            fill = "blue" if not r.is_main else "red"

            if not r.is_intersection:
                structure.append(
                    SceneRect(
                        insert=r.topleft(), size=Vec2(r.width, r.length), fill=fill
                    )
                )
            if opts.label_rooms:
                self.add_label(labels, r.center, str(i), opts)

            add_room_legend(i)

        if self.model.corridors is not None:

            line_kw = dict(stroke_width=3)

            def append_end_circles(ps, pe):
                structure.append(
                    SceneCircle(center=ps, r=opts.corridor_end_size, fill="green")
                )
                structure.append(
                    SceneCircle(center=pe, r=opts.corridor_end_size, fill="yellow")
                )

            for icor, cor in enumerate(self.model.corridors):

                colour = "blue"
                if len(cor.crosses):
                    colour = "yellow"
                if cor.entangled:
                    colour = "magenta"
                    # if cor.join_corridor == -1:
                    #     continue
                if cor.clipped > 1:
                    # clipped
                    colour = "orange"

                add_corridor_legend(icor)

                if len(cor.points) == 2:
                    p1, p2 = cor.points

                    structure.append(
                        SceneLine(start=p1, end=p2, stroke=colour, **line_kw)
                    )
                    append_end_circles(p1, p2)
                    if opts.label_corridors:
                        mid = Vec2((p1.x + p2.x) / 2.0, (p1.y + p2.y) / 2.0)
                        self.add_corridor_label(
                            labels, mid, str(icor), opts, colour="green"
                        )

                    continue

                p1, p2, p3 = cor.points  # its an elbow

                structure.append(SceneLine(start=p1, end=p2, stroke=colour, **line_kw))
                structure.append(SceneLine(start=p2, end=p3, stroke=colour, **line_kw))
                append_end_circles(p1, p3)
                if opts.label_corridors:
                    self.add_corridor_label(labels, p2, str(icor), opts, colour="green")

                # only render the alt if the primary is crossing
                if not len(cor.crosses):
                    continue

                if not cor.alternate:
                    continue

                p1, p2, p3 = cor.alternate  # its an elbow

                colour = "blue"
                if len(cor.alternate_crosses):
                    colour = "yellow"

                structure.append(SceneLine(start=p1, end=p2, stroke=colour, **line_kw))
                structure.append(SceneLine(start=p2, end=p3, stroke=colour, **line_kw))
                append_end_circles(p1, p3)

        return layers

    def render(self, gp, dwg, arena, opts: RenderOpts = None, base_tx=0.0, base_ty=0):

        if opts is None:
            opts = RenderOpts(gp=gp)
        if gp is not None:
            opts.grid = gp.tile_snap_size * opts.grid

        bbox, _ = rooms_bbox(self.model.rooms)

        gp = self.model.gp
        # setup global items
        self.add_markers(dwg)

        # build the scene
        layers = self.build_scene(bbox, gp, opts)

        # compute the translations
        w, h = bbox.width_height()
        # tx = w / 2.0 + avg.x
        # ty = h / 2.0 + avg.y
        tx = base_tx + w
        ty = base_ty + h

        def transform(x, y):
            x += tx
            y += ty
            x *= opts.scale
            y *= opts.scale
            return x, y
        
        # dwg.viewBox = ViewBox(minx=bbox.tl.x * opts.scale, miny = bbox.tl.y * opts.scale, width=w*opts.scale, height=h*opts.scale)
        dwg.viewbox(minx=bbox.tl.x * opts.scale, miny = bbox.tl.y * opts.scale, width=w*opts.scale, height=h*opts.scale)

        # render the scene

        for layer in layers:
            for si in layer:

                kw = dict(fill=si.fill, stroke=si.stroke, stroke_width=si.stroke_width)
                if si.attribs is not None:
                    kw.update(si.attribs)

                ri = None  # render item

                if isinstance(si, SceneLine):

                    x1, y1 = transform(si.start.x, si.start.y)
                    x2, y2 = transform(si.end.x, si.end.y)
                    ri = dwg.line(start=(x1, y1), end=(x2, y2), **kw)

                elif isinstance(si, SceneCircle):

                    x, y = transform(si.center.x, si.center.y)
                    r = si.r * opts.scale
                    ri = dwg.circle(center=(x, y), r=r, **kw)

                elif isinstance(si, SceneRect):

                    x, y = transform(si.insert.x, si.insert.y)
                    width = si.size.x * opts.scale
                    length = si.size.y * opts.scale

                    ri = dwg.rect(
                        insert=(x, y),
                        size=(width, length),
                        **kw,
                    )

                elif isinstance(si, ScenePoly):

                    points = []
                    for pt in si.points:
                        x, y = transform(pt.x, pt.y)
                        points.append([x, y])

                    ri = dwg.polygon(points=points, **kw)

                elif isinstance(si, ScenePolyline):

                    points = []
                    for pt in si.points:
                        x, y = transform(pt.x, pt.y)
                        points.append([x, y])

                    ri = dwg.polyline(points=points, **kw)

                elif isinstance(si, SceneText):
                    x, y = transform(si.insert.x, si.insert.y)

                    ri = dwg.text("", insert=(x, y))
                    ri.add(
                        dwg.tspan(
                            si.text,
                            font_size=si.font_size,
                            font_family=si.font_family,
                            font_weight=si.font_weight,
                            **kw,
                        )
                    )

                else:
                    print("unknown item", si)

                if ri is not None:
                    if si.class_:
                        ri["class"] = si.class_

                    el = arena.add(ri)
                    markers = getattr(si, "markers", None)
                    if markers is not None:
                        el.set_markers(markers)
                    opacity = getattr(si, "opacity", None)
                    if opacity is not None:
                        el.fill(opacity=opacity)
