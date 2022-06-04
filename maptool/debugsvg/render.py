"""rendering utilities for svg"""

import svgwrite
from svgwrite import cm, mm

from .datatypes import Vec2


def visdbg_split_box(name, g, box, a, b):
    dwg = svgwrite.Drawing(filename=name)
    arena = dwg.add(dwg.g(id="arena", fill="blue"))
    gp = g.gp
    scale = 15.0
    marginx = 20.0
    marginy = 20.0

    w, h = box.width_height()

    def insertion(x, y, tx=None, ty=None):
        x = marginx + ((x + gp.arena_size) / scale)
        y = marginy + ((y + gp.arena_size) / scale)
        if ty is not None:
            y = y + ty
        if tx is not None:
            x = x + tx
        return int(x) * mm, int(y) * mm

    def sizing(w, h):
        return int(w / scale) * mm, int(h / scale) * mm

    rect = dwg.rect(
        insert=insertion(box.tl.x, box.tl.y),
        size=sizing(w, h),
        stroke="red",
        stroke_width=3,
    )
    arena.add(rect)
    boxw, boxh = w, h

    transx = boxw / scale
    transy = boxh / scale

    w, h = a.width_height()
    if boxw == w:
        transx = None
    if boxh == h:
        transy = None

    rect = dwg.rect(
        fill="yellow",
        insert=insertion(a.tl.x, a.tl.y, tx=transx, ty=transy),
        size=sizing(w, h),
        stroke="black",
        stroke_width=2,
    )
    arena.add(rect)

    print(f"boxh: {boxh}, ah: {h}")

    w, h = b.width_height()
    rect = dwg.rect(
        fill="green",
        insert=insertion(b.tl.x, b.tl.y, tx=transx, ty=transy),
        size=sizing(w, h),
        stroke="black",
        stroke_width=2,
    )
    arena.add(rect)

    dwg.save()


def rooms(name, g):
    dwg = svgwrite.Drawing(filename=name)

    arena = dwg.add(dwg.g(id="arena", fill="blue"))

    gp = g.gp

    scale = 8.0

    # to account for the fact that we generate the centers randomly within the
    # arena circle translate by half the room size to keep everything on the
    # page. Note first 2 is the average, second is the halving
    transx = (gp.room_szmin + gp.room_szmax) / (2 * 2)
    transy = transx

    x = (transx + gp.arena_size) / scale
    y = (transy + gp.arena_size) / scale
    r = gp.arena_size / scale

    circle = dwg.circle(
        center=(int(x) * mm, int(y) * mm),
        r=int(r) * mm,
        fill="none",
        stroke="blue",
        stroke_width=3,
    )
    circle["class"] = "class1 class2"
    arena.add(circle)

    for r in g.rooms:

        pt = r.topleft()
        x = (transx + pt.x + gp.arena_size) / scale
        y = (transy + pt.y + gp.arena_size) / scale

        w = (r.width) / scale
        l = (r.length) / scale

        print(f"t: {x}, y: {y}, w: {w}, l: {l}")

        rect = dwg.rect(
            insert=(int(x) * mm, int(y) * mm),
            size=(int(w) * mm, int(l) * mm),
            stroke="red",
            stroke_width=3,
        )
        arena.add(rect)

    dwg.save()
