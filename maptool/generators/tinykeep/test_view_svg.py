from .view_svg import *
from maptool.datatypes import Vec2


def test_ctors():
    c = SceneCircle()
    assert c.fill == "black"
    c = SceneCircle(fill="red")
    assert c.fill == "red"

    rect = SceneRect(insert=Vec2(0.0, 0.0), fill="yellow")
    assert rect.insert.x == 0.0 and rect.insert.y == 0.0
    assert rect.fill == "yellow"
