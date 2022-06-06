from .datatypes import Box, Vec2
from .geometry import *

def test_hextrude_ideal():
    """

    +---+
    |b1 |    --     +---+
    |   |    shadow |
    |---+    --     |b2 |
                    |---+

    """

    b1 = Box(Vec2(1, 1), Vec2(5, 5))
    b2 = Box(Vec2(7, 3), Vec2(11, 7))

    ok, (a, b), sides = box_hextrude(b1, b2)

    assert ok
    assert sides[0] == RIGHT
    assert sides[1] == LEFT
    assert essentially_equal(a.x, 5)
    assert essentially_equal(b.x, 7)

def test_hextrude_ideal_inverted():
    """

    +---+
    |b2 |    --     +---+
    |   |    shadow |   |
    |---+    --     |b1 |
                    |---+

    """

    b1 = Box(Vec2(7, 3), Vec2(11, 7))
    b2 = Box(Vec2(1, 1), Vec2(5, 5))

    ok, (a, b), sides = box_hextrude(b1, b2)

    assert ok
    assert sides[0] == LEFT
    assert sides[1] == RIGHT
    assert essentially_equal(a.x, 7)
    assert essentially_equal(b.x, 5)


def test_vextrude_ideal():
    """
    +---+
    |b1 |
    |---+

       +---+
       |b2 |
       |---+

    """
    b1 = Box(Vec2(1, 1), Vec2(5, 5))
    b2 = Box(Vec2(3, 7), Vec2(7, 12))

    ok, (a, b), sides = box_vextrude(b1, b2)
    assert ok
    assert sides[0] == BOTTOM
    assert sides[1] == TOP
    assert essentially_equal(a.y, 5)
    assert essentially_equal(b.y, 7)


def test_vextrude_ideal_inverted():
    """
    +---+
    |b2 |
    |---+

       +---+
       |b1 |
       |---+

    """
    b1 = Box(Vec2(3, 7), Vec2(7, 12))
    b2 = Box(Vec2(1, 1), Vec2(5, 5))

    ok, (a, b), sides = box_vextrude(b1, b2)
    assert ok
    assert sides[0] == TOP
    assert sides[1] == BOTTOM
    assert essentially_equal(a.y, 7)
    assert essentially_equal(b.y, 5)