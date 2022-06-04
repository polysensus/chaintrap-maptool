from .datatypes import Box, Vec2
from .geometry import *


def test_pt_on_line_horizontal():

    l1 = Vec2(1.0,1.0)
    l2 = Vec2(5.0,1.0)
    p = Vec2(3.0,1.0)

    assert check_pt_on_line(p, l1, l2)

def test_pt_on_line_vertical():

    l1 = Vec2(1.0,1.0)
    l2 = Vec2(1.0,5.0)
    p = Vec2(1.0,3.0)

    assert check_pt_on_line(p, l1, l2)

def test_pt_on_line_diagonal():

    l1 = Vec2(1.0,1.0)
    l2 = Vec2(5.0,5.0)
    p = Vec2(3.0,3.0)

    assert check_pt_on_line(p, l1, l2)

def test_lines_colinear_and_equal():
    
    l1a = Vec2(1.0,1.0)
    l1b = Vec2(5.0,5.0)

    l2a = Vec2(1.0,1.0)
    l2b = Vec2(5.0,5.0)

    assert check_line_in_line(l1a, l1b, l2a, l2b)

    # when the lines are equal the test passes in both directions
    assert check_line_in_line(l2a, l2b, l1a, l1b)

def test_lines_not_paralel_diagonal():
    
    l1a = Vec2(1.0,1.0)
    l1b = Vec2(5.0,5.0)

    l2a = Vec2(1.0,1.0)
    l2b = Vec2(5.0,6.0)

    assert not check_line_in_line(l1a, l1b, l2a, l2b)

def test_lines_colinear_and_not_equal():
    
    l1a = Vec2(1.0,1.0)
    l1b = Vec2(5.0,5.0)

    l2a = Vec2(1.0,1.0)
    l2b = Vec2(7.0,7.0)

    assert check_line_in_line(l1a, l1b, l2a, l2b)
    assert not check_line_in_line(l2a, l2b, l1a, l1b)

def test_lines_colinear_perpendicular_not():
    """
    Test for the case where one line starts on the other
    """
    
    l1a = Vec2(1.0,1.0)
    l1b = Vec2(5.0,5.0)

    l2a = Vec2(3.0,3.0)
    l2b = Vec2(5.0,1.0)

    assert check_pt_on_line(l2a, l1a, l1b)
    assert not check_line_in_line(l2a, l2b, l1a, l1b)


def test_lines_colinear_consistent_horizontal():
    """check that check_line_in_line and line_line are consistent for horizontal and overlapping lines"""


    l1a = Vec2(1.0,1.0)
    l1b = Vec2(1.0,3.0)

    l2a = Vec2(1.0,1.0)
    l2b = Vec2(1.0,5.0)

    assert check_line_in_line(l1a, l1b, l2a, l2b)
    ok, pt = line_line(l1a, l1b, l2a, l2b)

    assert ok



def test_check_box_line_top():
    """

    +-|-+
    |   |
    +---+

    """

    box = Box(Vec2(2,2), Vec2(6, 6))
    p1 = Vec2(4, 1)
    p2 = Vec2(4, 4)

    assert check_box_line(box, p1, p2) == 0

def test_check_box_line_left():
    """

    +---+
    |   | 
   ---- |
    |   |
    +---+

    """

    box = Box(Vec2(2,2), Vec2(6, 6))
    p1 = Vec2(1, 4)
    p2 = Vec2(4, 4)

    assert check_box_line(box, p1, p2) == 1


def test_check_box_line_bot():
    """

    +---+
    |   |
    +-|-+

    """

    box = Box(Vec2(2,2), Vec2(6, 6))
    p1 = Vec2(4, 4)
    p2 = Vec2(4, 7)

    assert check_box_line(box, p1, p2) == 2


def test_check_box_line_right():
    """

    +---+
    |   | 
    |  ----
    |   |
    +---+

    """

    box = Box(Vec2(2,2), Vec2(6, 6))
    p1 = Vec2(3, 4)
    p2 = Vec2(7, 4)

    assert check_box_line(box, p1, p2) == 3



def test_box_valigned_a():
    """

    a) yes
    +---+
    |b1 |
    |---+

       +---+
       |b2 |
       |---+
    """

    b1 = Box(Vec2(1, 1), Vec2(5, 5))
    b2 = Box(Vec2(3, 7), Vec2(7, 12))

    assert box_valigned(b1, b2)
    assert box_valigned(b2, b1)
    assert not box_haligned(b1, b2)
    assert not box_haligned(b2, b1)


def test_box_not_valigned_or_haligned():
    """

    +---+
    |b1 |
    |---+

          +---+
          |b2 |
          |---+
    """

    b1 = Box(Vec2(1, 1), Vec2(5, 5))
    b2 = Box(Vec2(7, 7), Vec2(11, 12))

    assert not box_valigned(b1, b2)
    assert not box_valigned(b2, b1)
    assert not box_haligned(b1, b2)
    assert not box_haligned(b2, b1)


def test_box_intersect():
    """

    a) yes
    +---+
    |b1 |
    |  +---+
    |---+  |
       |b2 |
       |---+
    """

    b1 = Box(Vec2(1, 1), Vec2(5, 5))
    b2 = Box(Vec2(3, 4), Vec2(7, 12))

    assert box_valigned(b1, b2)
    assert box_valigned(b2, b1)
    assert box_haligned(b1, b2)
    assert box_haligned(b2, b1)
    assert box_intersect(b1, b2)
    assert box_intersect(b2, b1)


def test_box_haligned():
    """

    a) yes
    +---+
    |b1 |  +---+
    |---+  |b2 |
           |---+
    """

    b1 = Box(Vec2(1, 1), Vec2(5, 5))
    b2 = Box(Vec2(7, 3), Vec2(11, 7))

    assert box_haligned(b1, b2)
    assert box_haligned(b2, b1)

    assert not box_valigned(b1, b2)
    assert not box_valigned(b2, b1)
