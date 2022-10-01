import pytest

from maptool.generators.tinykeep.model import Generator
from maptool.map import Map
from maptool.room import RoomSide

NORTH = RoomSide.NORTH
WEST = RoomSide.WEST
SOUTH = RoomSide.SOUTH
EAST = RoomSide.EAST


@pytest.fixture
def emptymodel():
    g = Generator()
    # g._reset_generator(Map(Map.defaults()).gp)
    m = Map(Map.defaults())
    m.new_proof()
    g._reset_generator(m.gp)
    return g
