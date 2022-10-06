import pytest
import secrets
import json
from .map import Map
from .map import run
from .randprimitives import rand_box, rand_split_box
from .geometry import *


def test_generator_init_noargs():
    g = Map(None)
    g.new_proof()
    v = g.vrf_inputs(format=None)
    assert v['alpha']
    assert v['proof']
    assert v['seed']
    assert v['secret']


def test_generator_init_bothargs():

    args = Map.defaults()
    args = type('args', (), dict(
        secret = secrets.token_bytes(nbytes=32).hex(),
        seed = secrets.token_bytes(nbytes=8).hex()))()
    g = Map(args)
    g.new_proof()
    v = g.vrf_inputs(format=None)
    assert v['alpha']
    assert v['proof']
    assert 'seed' not in v
    assert 'secret' not in v


def test_generator_vrf_inputs():

    args = Map.defaults()
    args.secret = secrets.token_bytes(nbytes=32).hex()
    args.seed = secrets.token_bytes(nbytes=8).hex()
    g = Map.from_args(args)
    doc = g.vrf_inputs()
    assert isinstance(doc, str)
    r = json.loads(doc)
    assert "secret" not in r
    assert "seed" not in r


@pytest.mark.parametrize(
    "note,seed,secret",
    [
        (
            "regression-demo-map",
            "9c9d1793f1e2c6db",
            "b6eb87339ec3b87f70308f471e02b544325e88f30bd56e8bf9ff530cb1223325",
        ),
        (
            "regression-clip-indirectly-disentangles",
            b"K\x92\xa1o\xa6\xff\xc4\x0c".hex(),
            b"\x11\x19)~\xcc]\\5\x94\xfe\x92\xea\x0e\xca \x85\xbbd^\x9b\xf7GN\xcc\\\xa7u3\xc3q)k".hex(),
        ),
        (
            "regression-2",
            "e7357c72ae6861ae",
            "a23cccec37055701674748316860eac927212048f0666ea02ef0bf1737e2195e",
        ),
        (
            "regression-3",
            "49febb61d5f15e9e",
            "a80a2426333f59f9b585d8e6698d01163f959dbd196d44d43d35b4ce699646d0",
        ),
        ("random", None, None),
    ],
)
def test_generator_deterministic(note, seed, secret):

    print(note)
    args = Map.defaults()
    args.gp_model = "tinykeep"
    if seed is None:
        seed = secrets.token_bytes(nbytes=8).hex()
    if secret is None:
        secret = secrets.token_bytes(nbytes=32).hex()
    args.seed = seed
    args.secret = secret

    g = Map.from_args(args)
    g.generate()
    rooms1 = g.model.rooms
    g.generate()
    rooms2 = g.model.rooms  # should be different

    g.reseed_rng()
    g.generate()
    rooms3 = g.model.rooms  # should be different

    assert rooms1 != rooms2
    assert rooms1 == rooms3

def test_commit_and_generate():

    gp = Map.defaults_dict()
    args = type('args', (), dict([('gp_' + k, v) for k, v in gp.items()]))
    args.seed = None
    args.secret = None
    map = Map.from_args(args)
    vrf_inputs = map.vrf_inputs(format=None)

    map = Map(None)
    map.set_vrf_inputs(vrf_inputs)
    map.generate()
    j = map.tojson(dumps=False)



def rooms_eq(ra, rb, ignore_isolated=False, ignore_main=False):

    # round tripping via json is not numerically stable.
    if not pt_essentially_same(ra.center, rb.center):
        return False

    if not essentially_equal(ra.width, rb.width):
        return False
    if not essentially_equal(ra.length, rb.length):
        return False
    if not ignore_main and ra.is_main != rb.is_main:
        return False

    if ra.corridors is None:
        if rb.corridors is None:
            return False
        return True

    if rb.corridors is None:
        return False

    for i, sidea in enumerate(ra.corridors):
        if ignore_isolated:
            if not sidea or not rb.corridors[i]:
                continue
        if sidea != rb.corridors[i]:
            return False
    return True


def corridors_eq(ca, cb):
    if ca.joins[0] != cb.joins[0]:
        return False
    if ca.joins[1] != cb.joins[1]:
        return False

    if ca.join_sides[0] != cb.join_sides[0]:
        return False
    if ca.join_sides[1] != cb.join_sides[1]:
        return False

    if len(ca.points) != len(cb.points):
        return False

    for i, pa in enumerate(ca.points):
        if not pt_essentially_same(pa, cb.points[i]):
            return False

    return True


def test_rooms_persist():

    args = Map.defaults()
    args.gp_model = "tinykeep"
    g = Map.from_args(args)
    g.generate()
    rooms1 = g.model.rooms[:]
    corridors1 = g.model.corridors[:]
    source = g.tojson(dumps=True)

    g = Map(args)

    map = g.load_common(source)
    g.model = g.import_model(map["model_type"])
    g.model._reset_generator(g.gp)
    g.model.load_rooms(g, map["model"])

    assert len(rooms1) == len(g.model.rooms)

    for (i, r) in enumerate(rooms1):
        # corridors and is_main are set post load
        assert rooms_eq(r, g.model.rooms[i], ignore_isolated=True, ignore_main=True)

    g.model.load_corridors(g, map["model"])
    for (i, c) in enumerate(corridors1):
        # corridors and is_main are set post load
        assert corridors_eq(c, g.model.corridors[i])


def test_generator_persist():

    args = Map.defaults()
    args.gp_model = "tinykeep"
    g = Map.from_args(args)
    g.generate()
    rooms1 = g.model.rooms

    source = g.tojson(dumps=True)
    g = Map.from_source(args, source)

    for (i, r) in enumerate(rooms1):
        if rooms_eq(r, g.model.rooms[i]):
            print("x")
        assert rooms_eq(r, g.model.rooms[i])


def test_run():
    status = run(args=["gen", "--svgfile", "x.svg"])
    assert status == 0
