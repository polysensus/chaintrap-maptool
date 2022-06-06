"""
box_lextrude test cases


    +-----+b1_i
    |b1   |-----+
    +-----+     |
        |      +-----+
        +______|b2   |
               |     |
               +-----+

               +-----+
        +____  |b2   |
        |      +-----+
    +-----+      |
    |b1   |------+
    +-----+ b1_i


"""

import pytest
from maptool.geometry import *

@pytest.fixture
def box_tl_br():
    """

    +---+
    |b1 |
    +---+

          +---+
          |b2 |
          +---+
    """

    b1 = Box(Vec2(1, 1), Vec2(5, 5))
    b2 = Box(Vec2(7, 7), Vec2(11, 12))

    return b1, b2


@pytest.fixture
def box_bl_tr():
    """
          +---+
          |b2 |
          +---+

    +---+
    |b1 |
    +---+

    """

    b1 = Box(Vec2(1, 7), Vec2(5, 12))
    b2 = Box(Vec2(7, 1), Vec2(11, 6))

    return [(b1, b2), (b2, b1)]

def test_bl_tr(box_bl_tr):
    for b1, b2 in box_bl_tr:
        (line1, join1), (line2, join2) = box_lextrude(b1, b2)

        # b1 -> b2 first
        if join1[0] == TOP:
            # path up and accross was shorter (or equal)
            assert join1[1] == LEFT
            assert join2[0] == RIGHT
            assert join2[1] == BOTTOM
        elif join1[0] == RIGHT:
            # path accross and up was shorter
            # line1 will go accross then up
            assert join1[1] == BOTTOM
            # line2 will go up then accross
            assert join2[0] == TOP
            assert join2[1] == LEFT

            assert essentially_equal(line1[0].x, 5)
            assert essentially_equal(line1[2].y, 6)

            assert essentially_equal(line2[0].y, 7)
            assert essentially_equal(line2[2].x, 7)
        # b2 -> b1 cases
        elif join1[0] == BOTTOM:
            assert join1[1] == RIGHT
            assert essentially_equal(line1[0].y, 6)
            assert essentially_equal(line1[2].x, 5)

            assert join2[0] == LEFT
            assert join2[1] == TOP

            pass
        else:
            assert join1[0] == LEFT
            assert join1[1] == TOP
            assert join2[0] == BOTTOM
            assert join2[1] == RIGHT



