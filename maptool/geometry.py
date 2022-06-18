"""various geomtric utilities

line intersection with aabb usies Liang-Barsky. See:

* https://gist.github.com/ChickenProp/3194723
* https://en.wikipedia.org/wiki/Liang%E2%80%93Barsky_algorithm
* https://www.jeffreythompson.org/collision-detection
"""
from typing import Tuple
import sys
import math

from .datatypes import Error, Box, Vec2

TOP=0
LEFT=1
BOTTOM=2
RIGHT=3

class GeometryError(Error):
    """An error with the math, geometry or spatial logic"""

def essentially_zero(x):
    e = sys.float_info.epsilon * 2
    return x >= -e and x <= e

def essentially_equal(a, b):
    return essentially_zero(a - b)

def essentially_lt(a, b):
    e = sys.float_info.epsilon * 2
    return (a + e) < b

def pt_within_radi2(p: Vec2, c: Vec2, radi2: float):
    dx = p.x - c.x
    dy = p.y - c.y
    if dx * dx + dy * dy < radi2:
        return True
    return False

def pt_dist2(p1: Vec2, p2: Vec2) -> float:
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    return dx*dx+dy*dy

def pt_dist(p1: Vec2, p2: Vec2) -> float:
    return math.sqrt(pt_dist2(p1, p2))

def pt_essentially_same(p1: Vec2, p2: Vec2) -> float:
    x = math.sqrt(pt_dist2(p1, p2))
    return essentially_zero(x)

def check_pt_dist(p1: Vec2, p2: Vec2, dist: float) -> bool:
    x = math.sqrt(pt_dist2(p1, p2))
    return x < dist

def check_pt_on_line(p, l1, l2, margin=0.1) -> bool:

    line_len = pt_dist(l1, l2)
    d1 = pt_dist(p, l1)
    d2 = pt_dist(p, l2)

    # the only situation where d1 and d2 can be equal is if the point is on the
    # line. we allow margin due to float precission
    x = d1 + d2
    if x >= line_len-margin and x <=line_len + margin:
        return True
    return False

def check_line_in_line(l1a, l1b, l2a, l2b, margin=0.1) -> bool:
    """ if l1 is completely contained by l1
    
    Note that if they are co linear and l2 is shorter than l1 then the test fails.
    So, depending on context, you may need to call twice."""

    if not check_pt_on_line(l1a, l2a, l2b, margin=margin):
        return False

    if not check_pt_on_line(l1b, l2a, l2b, margin=margin):
        return False
    
    return True

def xline_in_line(p1, p2, p3, p4) -> Tuple[bool, Vec2, Vec2]:
    """for cases where the lines are co-linear, return the pt(s) of overlap"""

    p1_on = check_pt_on_line(p1, p3, p4)
    p2_on = check_pt_on_line(p2, p3, p4)

    if not (p1_on or p2_on):
        return (False, None, None)

    if (p1_on and p2_on):
        return (True, p1, p2)

    if p1_on:
        return (True, p1, None)
    return (True, None, p2)


def line_in_line(p1, p2, p3, p4) -> Tuple[bool, Vec2]:
    """for cases where the lines are co-linear, return the pt(s) of overlap

    heuristic favouring corridor cliping: if the second point is on or in always return it
    otherwise return the first point only if it is on or in

    """
    ok, a, b = xline_in_line(p1, p2, p3, p4)
    if not ok:
        return (False, None)
    
    if b is not None:
        return (True, b)
    
    return (True, a)


def parallel(p1: Vec2, p2: Vec2, p3: Vec2, p4: Vec2) -> bool:
    divisor = ((p4.y-p3.y) * (p2.x-p1.x) - (p4.x-p3.x)*(p2.y-p1.y))
    if essentially_zero(divisor):
        return True
    return False


def line_line(p1: Vec2, p2: Vec2, p3: Vec2, p4: Vec2) -> Tuple[bool, Vec2]:
    """check for line intersection"""

    # uA = ((x4-x3)*(y1-y3) - (y4-y3)*(x1-x3)) / ((y4-y3)*(x2-x1) - (x4-x3)*(y2-y1))

    # check for infinities

    divisor = ((p4.y-p3.y) * (p2.x-p1.x) - (p4.x-p3.x)*(p2.y-p1.y))
    if essentially_zero(divisor):
        # catch the parallel case
        return line_in_line(p1, p2, p3, p4)

    ua = ((p4.x - p3.x)*(p1.y-p3.y) - (p4.y-p3.y)*(p1.x-p3.x)) / divisor

    # uB = ((x2-x1)*(y1-y3) - (y2-y1)*(x1-x3)) / ((y4-y3)*(x2-x1) - (x4-x3)*(y2-y1))

    divisor = ((p4.y-p3.y)*(p2.x-p1.x) - (p4.x-p3.x)*(p2.y-p1.y))
    if essentially_zero(divisor):
        return line_in_line(p1, p2, p3, p4)

    ub = ((p2.x-p1.x)*(p1.y-p3.y) - (p2.y-p1.y)*(p1.x-p3.x)) / divisor

    if ua <=0.0 or ua <= 1.0 or ub >=0.0 or ub <= 1.0:
        return (False, Vec2())
    # if there is a colision 0 <= ua and ub <= 1
    #if ua >=0.0 and ua <= 1.0 and ub >=0.0 and ub <= 1.0:
    #    return True

    return (True, Vec2(p1.x + ua * (p2.x - p1.x), p1.y + (ua * (p2.y - p1.y))))


def check_line_line(p1: Vec2, p2: Vec2, p3: Vec2, p4: Vec2) -> bool:
    """check for line intersection"""

    # uA = ((x4-x3)*(y1-y3) - (y4-y3)*(x1-x3)) / ((y4-y3)*(x2-x1) - (x4-x3)*(y2-y1))

    # check for infinities

    divisor = ((p4.y-p3.y) * (p2.x-p1.x) - (p4.x-p3.x)*(p2.y-p1.y))
    if essentially_zero(divisor):
        return False

    ua = ((p4.x - p3.x)*(p1.y-p3.y) - (p4.y-p3.y)*(p1.x-p3.x)) / divisor

    # uB = ((x2-x1)*(y1-y3) - (y2-y1)*(x1-x3)) / ((y4-y3)*(x2-x1) - (x4-x3)*(y2-y1))

    divisor = ((p4.y-p3.y)*(p2.x-p1.x) - (p4.x-p3.x)*(p2.y-p1.y))
    if essentially_zero(divisor):
        return False

    ub = ((p2.x-p1.x)*(p1.y-p3.y) - (p2.y-p1.y)*(p1.x-p3.x)) / divisor

    # if there is a colision 0 <= ua and ub <= 1
    if ua >=0.0 and ua <= 1.0 and ub >=0.0 and ub <= 1.0:
        return True

    return False


def check_box_line(b: Box, p1: Vec2, p2: Vec2) -> int:
    """return an integer indicating which box side is intersected by the line or -1 if it doesn't
    
    anticlockwise from top:

    top = 0, left =1, bottom=2, right=3
    """

    # top side
    if check_line_line(b.tl, Vec2(b.br.x, b.tl.y), p1, p2):
        return TOP

    # left side
    if check_line_line(b.tl, Vec2(b.tl.x, b.br.y), p1, p2):
        return LEFT
    # bottom
    if check_line_line(Vec2(b.tl.x, b.br.y), b.br, p1, p2):
        return BOTTOM

    # right side
    if check_line_line(Vec2(b.br.x, b.tl.y), Vec2(b.br.x, b.br.y), p1, p2):
        return RIGHT
    
    return -1


def box_valigned(b1: Box, b2: Box) -> bool:

    x_left = max(b1.tl.x, b2.tl.x)
    x_right = min(b1.br.x, b2.br.x)

    if x_right < x_left:
        return False

    return True


def box_vshadow(b1: Box, b2: Box) -> float:

    x_left = max(b1.tl.x, b2.tl.x)
    x_right = min(b1.br.x, b2.br.x)

    if x_right < x_left:
        return 0.0

    return x_right - x_left


def box_haligned(b1: Box, b2) -> bool:

    y_top = max(b1.tl.y, b2.tl.y)
    y_bot = min(b1.br.y, b2.br.y)

    if y_bot < y_top:
        return False

    return True


def box_hshadow(b1: Box, b2) -> float:

    y_top = max(b1.tl.y, b2.tl.y)
    y_bot = min(b1.br.y, b2.br.y)

    if y_bot < y_top:
        return 0.0

    return y_bot - y_top


def box_not_aligned(b1: Box, b2: Box) -> bool:
    return not (box_haligned(b1, b2) or box_valigned(b1, b2))


def box_intersect(b1, b2):
    return box_haligned(b1, b2) and box_valigned(b1, b2)


def box_hextrude(b1, b2, factor=0.5, min=0.0):
    """extrude a connecting line between two boxes that are assumed not to be intersecting

    horizontal case
    +---+
    |b1 |    --     +---+
    |   |    shadow |
    |---+    --     |b2 |
                    |---+

    """

    shadow = box_hshadow(b1, b2)
    if shadow <= min:
        return False, (None, None), (None, None)

    # inverted case b2 -> b1 ?
    swaped = False
    if b1.br.x > b2.tl.x:
        b2, b1 = b1, b2
        swaped = True

    # b1 vertically lower (larger y) than b2 ?
    if b1.tl.y >= b2.tl.y:
        y0, y1 = b1.tl.y, b2.br.y
    else:
        y0, y1 = b2.tl.y, b2.br.y

    iy = y0 + (y1 - y0) * factor

    p1 = Vec2(b1.br.x, iy)
    p2 = Vec2(b2.tl.x, iy)

    # inverted case b2 -> b1 (remembering we swaped b1, b2 above) ?
    if swaped:
        return True, (p2, p1), (LEFT, RIGHT)
    else:
        return True, (p1, p2), (RIGHT, LEFT)


def box_vextrude(b1, b2, factor=0.5, min=0.0):
    """vertically extrude a connecting line between two boxes that are assumed not to be intersecting

    +-----+
    |b1   |
    |-----+
       |sh|adow
       +-----+
       |b2   |
       |-----+


    """

    # inverted case b2 -> b1 ?
    swaped = False
    if b1.tl.y > b2.tl.y:
        b1, b2 = b2, b1
        swaped = True

    shadow = box_vshadow(b1, b2)
    if shadow <= min:
        return False, (None, None), (None, None)

    b1_i = Vec2(b2.tl.x, b1.br.y)
    b2_i = Vec2(b1.br.x, b2.tl.y)

    ix = b1_i.x + (b2_i.x - b1_i.x) * factor
    p1 = Vec2(ix, b1.br.y)
    p2 = Vec2(ix, b2.tl.y)

    if swaped:
        return True, (p2, p1), (TOP, BOTTOM)
    else:
        return True, (p1, p2), (BOTTOM, TOP)


def dist2(a: Vec2, b: Vec2) -> float:
    return (b.x - a.x) ** 2 + (b.y - a.y) ** 2


def identify_ends(points):
    """
    TODO: We could probably infer this directly. but its pain and just checking
    the geometry is easy"""

    def _identify_ends(points):

        p1, p2, p3 = points

        # if the first two x's are equal we must have:
        #  a) |__ or b)  +--+
        #                |
        if essentially_equal(p1.x, p2.x):
            if p1.y < p2.y:
                # it's a) p1 is leaving the BOTTOM and p2 is entering LEFT
                if p2.x < p3.x:
                    return BOTTOM, LEFT
                else:
                    return BOTTOM, RIGHT
            # it's b) p1 is leaving the TOP and p2 is entering LEFT
            if p2.x < p3.x:
                return TOP, LEFT
            else:
                return TOP, RIGHT
 
        # ok, it must be
        #   --+  or b) |
        #  a) |      --+
        assert essentially_equal(p2.x, p3.x)
        if p2.y < p3.y:
            # it's a) leaving LEFT and entering TOP
            if p1.x < p2.x:
                return RIGHT, TOP
            else:
                return LEFT, TOP

        # it's b) leaving LEFT and entering BOTTOM
        if p1.x < p2.x:
            return RIGHT, BOTTOM
        else:
            return LEFT, BOTTOM

    return points, _identify_ends(points)


def box_lextrude(b0, b1, factor=0.5, min=0.0):

    """assume the boxes are neither horizonatly nor verticaly aligned and create
    a pair of elbows. The caller can pick the one they like

                           We deal with the opposite cases by flipping the points around
    +-----+b1_i            +-----+b2_i
    |b1   |-----+          |b2   |-----+
    +-----+     |          +-----+     |
        |      +-----+         |      +-----+
        +______|b2   |         +______|b1   |
               |     |                |     |
               +-----+                +-----+

               +-----+                +-----+
        +____  |b2   |         +____  |b1   |
        |      +-----+         |      +-----+
    +-----+      |         +-----+      |
    |b1   |------+         |b2   |------+
    +-----+ b1_i           +-----+ b2_i
    """

    # TODO: thought we needed to explicitly allow for inverse cases. But it
    # seems best to check for the caller to check those and pass in b0 and b1 in
    # a consistent layout. So can simplify accordingly and use b0, b1 directly
    b = [b0, b1]

    ib0, ib1 = 0, 1
    assert b[0].tl.x < b[1].tl.x

    b0_right_i = Vec2(b[ib0].br.x, b[ib0].tl.y + (b[ib0].br.y - b[ib0].tl.y) * factor)
    b1_left_i = Vec2(b[ib1].tl.x, b[ib1].tl.y + (b[ib1].br.y - b[ib1].tl.y) * factor)

    b0_top_i = Vec2(b[ib0].tl.x + (b[ib0].br.x - b[ib0].tl.x) * factor, b[ib0].tl.y)
    b0_bot_i = Vec2(b[ib0].tl.x + (b[ib0].br.x - b[ib0].tl.x) * factor, b[ib0].br.y)

    b1_top_i = Vec2(b[ib1].tl.x + (b[ib1].br.x - b[ib1].tl.x) * factor, b[ib1].tl.y)
    b1_bot_i = Vec2(b[ib1].tl.x + (b[ib1].br.x - b[ib1].tl.x) * factor, b[ib1].br.y)

    # b1 right to b2 top
    # +-----+b1_i            +-----+b2_i
    # |b1   |-----+          |b2   |-----+
    # +-----+     |          +-----+     |
    #     |      +-----+         |      +-----+
    #     +______|b2   |         +______|b1   |
    #            |     |                |     |
    #            +-----+                +-----+
    if b[ib0].br.y < b[ib1].tl.y:

        el_right_top = (b0_right_i, Vec2(b1_top_i.x, b0_right_i.y), b1_top_i)
        el_bot_left = (b0_bot_i, Vec2(b0_bot_i.x, b1_left_i.y), b1_left_i)

        # return the shortest first
        d2_right_top = dist2(el_right_top[0], el_right_top[1])
        d2_right_top += dist2(el_right_top[1], el_right_top[2])
        d2_bot_left = dist2(el_bot_left[0], el_bot_left[1])
        d2_bot_left += dist2(el_bot_left[1], el_bot_left[2])

        if d2_right_top < d2_bot_left:

            join1, join2 = [None, None], [None, None]

            join1[ib0], join1[ib1] = (RIGHT, TOP)
            join2[ib0], join2[ib1] = (BOTTOM, LEFT)

            return (el_right_top, join1), (el_bot_left, join2)

        else:
            join1, join2 = [None, None], [None, None]

            join1[ib0], join1[ib1] = (BOTTOM, LEFT)
            join2[ib0], join2[ib1] = (RIGHT, TOP)

            return (el_bot_left, join1), (el_right_top, join2)

    # b1 top to b2 left
    #            +-----+                +-----+
    #     +____  |b2   |         +____  |b1   |
    #     |      +-----+         |      +-----+
    # +-----+      |         +-----+      |
    # |b1   |------+         |b2   |------+
    # +-----+ b1_i           +-----+ b2_i

    el_top_left = (b0_top_i, Vec2(b0_top_i.x, b1_left_i.y), b1_left_i)
    el_right_bot = (b0_right_i, Vec2(b1_bot_i.x, b0_right_i.y), b1_bot_i)

    d2_top_left = dist2(el_top_left[0], el_top_left[1])
    d2_top_left += dist2(el_top_left[1], el_top_left[2])
    d2_right_bot = dist2(el_right_bot[0], el_right_bot[1])
    d2_right_bot += dist2(el_right_bot[1], el_right_bot[1])

    if d2_top_left < d2_right_bot:
        join1, join2 = [None, None], [None, None]

        join1[ib0], join1[ib1] = (TOP, LEFT)
        join2[ib0], join2[ib1] = (RIGHT, BOTTOM)

        return (el_top_left, join1), (el_right_bot, join2)

    else:
        join1, join2 = [None, None], [None, None]

        join1[ib0], join1[ib1] = (RIGHT, BOTTOM)
        join2[ib0], join2[ib1] = (TOP, LEFT)

        return (el_right_bot, join1), (el_top_left, join2)