"""generate various random primitives"""

import math
import random
from .datatypes import Vec2, Box, GenArena

from .room import Room, GenRoom


def round(n: float, m: float):
    """To support tiled grids we need to round in a predictable way

    Arguments:
    n: the value to round
    m: the snap resolution"""
    return math.floor(((n + m - 1.0)) / m) * m


def rand_cointoss(bias=0.5) -> bool:
    return random.random() > bias


def rand_point_in_circle(radius: float, tile_snap_size: float) -> Vec2:
    """Generate a point at a random position within a circle"""

    t = 2.0 * math.pi * random.random()
    u = random.random() + random.random()
    r = 2.0 - u if u > 1.0 else u
    x = radius * r * math.cos(t)
    y = radius * r * math.sin(t)
    return Vec2(round(x, tile_snap_size), round(y, tile_snap_size))


def rand_box(s1: float, s2: float, ratio: float, snap: float):

    if rand_cointoss():
        w1, w2 = s1, s2
        l1, l2 = s1 * ratio, s2 * ratio
    else:
        l1, l2 = s1, s2
        w1, w2 = s1 * ratio, s2 * ratio

    w = round(random.uniform(w1, w2), snap * 2)
    l = round(random.uniform(l1, l2), snap * 2)
    tl = Vec2(-w / 2, -l / 2)
    br = Vec2(w / 2, l / 2)
    return Box(tl, br)


def rand_split_box(box):
    """split box supports bsp based generation"""

    splitfactor = random.random()

    if rand_cointoss():
        # split vertical axis

        # tl
        #    |___ br2 __ ysplit
        # tl2
        #    |___ br

        ysplit = (box.br.y - box.tl.y) / splitfactor

        tl2 = Vec2(box.tl.x, box.tl.y + ysplit)
        br2 = Vec2(box.br.x, box.tl.y + ysplit)

        # top box tl remains the same
        top = Box(box.tl, br2)

        # bottom box br remains the same
        bot = Box(tl2, box.br)
        return top, bot

    # otherwise, split horizontal
    # tl  tl2
    #   |_|__ br
    #     |
    #     br2
    #     xsplit

    xsplit = (box.br.x - box.tl.x) / splitfactor

    tl2 = Vec2(box.tl.x + xsplit, box.tl.y)
    br2 = Vec2(box.tl.x + xsplit, box.br.y)
    # left box tl remains the same
    left = Box(box.tl, br2)
    # right box br remains the sanme
    right = Box(tl2, box.br)

    return left, right


def rand_room(ag: GenArena, rg: GenRoom) -> Room:

    c = rand_point_in_circle(ag.arena_size, ag.tile_snap_size)

    if rand_cointoss():
        w1, w2 = rg.s1, rg.s2
        l1, l2 = rg.s1 * rg.ratio, rg.s2 * rg.ratio
    else:
        l1, l2 = rg.s1, rg.s2
        w1, w2 = rg.s1 * rg.ratio, rg.s2 * rg.ratio

    w = round(random.uniform(w1, w2), ag.tile_snap_size)
    l = round(random.uniform(l1, l2), ag.tile_snap_size)
    return Room(center=c, width=w, length=l)
