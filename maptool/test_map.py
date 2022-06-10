import secrets
import json
from .map import Map
from .map import run
from .randprimitives import rand_box, rand_split_box


def test_generator_init_noargs():
    args = Map.defaults()
    g = Map(args)
    assert g._generated_seed is True
    assert g._generated_secret is True


def test_generator_init_bothargs():

    args = Map.defaults()
    args.secret = secrets.token_bytes(nbytes=32).hex()
    args.seed = secrets.token_bytes(nbytes=8).hex()
    g = Map(args)
    assert g._generated_seed is False
    assert g._generated_secret is False
    assert args.seed in g._alpha.decode()
    assert args.secret not in g._alpha.decode()


def test_generator_vrf_inputs():

    args = Map.defaults()
    args.secret = secrets.token_bytes(nbytes=32).hex()
    args.seed = secrets.token_bytes(nbytes=8).hex()
    g = Map(args)
    doc = g.vrf_inputs()
    assert isinstance(doc, str)
    r = json.loads(doc)
    assert "secret" not in r
    assert args.seed == r["seed"]
    assert args.seed in r["alpha"]


def test_generator_deterministic():

    args = Map.defaults()
    args.gp_model = "tinykeep"
    g = Map(args)
    g.generate()
    rooms1 = g.model.rooms
    g.generate()
    rooms2 = g.model.rooms  # should be different

    g.reseed_rng()
    g.generate()
    rooms3 = g.model.rooms  # should be different

    assert rooms1 != rooms2
    assert rooms1 == rooms3


def test_generator_persist():

    args = Map.defaults()
    args.gp_model = "tinykeep"
    g = Map(args)
    g.generate()
    rooms1 = g.model.rooms

    source = g.tojson(dumps=True)
    g = Map(args)
    g.load(source)

    for (i, r) in enumerate(rooms1):
        if r != g.model.rooms[i]:
            print('x')
        assert r == g.model.rooms[i]

def test_run():
    status = run(args=["gen", "--svgfile", "x.svg"])
    assert status == 0
