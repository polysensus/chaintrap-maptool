"""map generation"""
import sys
import io
import argparse
import secrets
import json
import random
import pickle
import importlib
from pathlib import Path
import svgwrite
import vrf.ec
from vrf.ec import ecvrf_prove, ecvrf_proof_to_hash
from .clicommon import run_status


class Error(Exception):
    """General error in the map tool"""


class SeedError(Error):
    """Error generating the map seed"""


# ref: https://www.gamedeveloper.com/programming/procedural-dungeon-generation-algorithm
# ref: Prodedural Content Generation in Games (Computational Synthesis and Creative Systems)


class Map:

    _version = 1
    _variant = 1

    # generation parameters
    default_model = "tinykeep"
    default_arena_size = 512 * 4.0
    default_corridor_redundancy = 15.0  # 15 percent
    default_flock_factor = 600.0
    default_main_room_thresh = 0.8
    default_min_separation_factor = 1.7
    default_room_szmax = default_arena_size / 2.0
    default_room_szmin = default_arena_size / 4.0
    default_room_szratio = 1.8
    default_rooms = 16
    default_tan_fudge = 0.0001
    default_tile_snap_size = 4.0

    @classmethod
    def defaults(cls):
        return type(
            "MapArgs",
            (),
            dict(
                # gp_ indicates generation parameter. all gp_ prefixed attributes
                # are automatically included in the vrf alpha
                gp_model=cls.default_model,
                gp_arena_size=cls.default_arena_size,
                gp_corridor_redundancy=cls.default_corridor_redundancy,
                gp_flock_factor=cls.default_flock_factor,
                gp_main_room_thresh=cls.default_main_room_thresh,
                gp_min_separation_factor=cls.default_min_separation_factor,
                gp_room_szmax=cls.default_room_szmax,
                gp_room_szmin=cls.default_room_szmin,
                gp_room_szratio=cls.default_room_szratio,
                gp_rooms=cls.default_rooms,
                gp_tan_fudge=cls.default_tan_fudge,
                gp_tile_snap_size=cls.default_tile_snap_size,
                secret=None,
                seed=None,
                debug=False,
                svgfile=None,
                render_generations=-1,
                no_label_rooms=False,
                no_label_corridors=False,
                no_legend=False,
            ),
        )

    def __init__(self, args):

        self.args = args

        # If the user provided a private key, use it. Otherwise generate one
        self._generated_secret = False
        secret = args.secret
        if secret is not None:
            secret = bytes.fromhex(secret)
        if secret is None:
            secret = secrets.token_bytes(nbytes=32)
            self._generated_secret = True
        self._secret = secret

        # If the user provided a seed, use it. Otherwise generate one
        self._generated_seed = False
        seed = args.seed
        if seed is not None:
            seed = bytes.fromhex(seed)
        if seed is None:
            seed = secrets.token_bytes(nbytes=8)
            self._generated_seed = True
        self._seed = seed

        self._gp = dict()
        for k, v in args.__dict__.items():
            if k.startswith("gp_"):
                self._gp[k[3:]] = v

        gp = ",".join([f"{k}={v}" for k, v in self._gp.items()])

        # Only the holder of the secret can prove
        # a) they generated the map
        # b) what the map generation inputs were
        self._alpha = (
            f"{self._version}:{self._variant}:{self._seed.hex()}:{gp}".encode()
        )

        self._public_key = vrf.ec.get_public_key(self._secret)
        p_status, pi = ecvrf_prove(self._secret, self._alpha)
        if p_status != "VALID":
            raise SeedError("failed to generate seed and paramaters proof")

        b_status, beta = ecvrf_proof_to_hash(pi)
        if b_status != "VALID":
            raise SeedError("failed to derive hash from seed proof")

        self._pi = pi
        self._beta = beta
        self.reseed_rng()

    @property
    def gp(self):
        return type("GenerationParams", (), self._gp)

    def reseed_rng(self):
        """Re seed the rng so the geneartor can run again with the current parameters"""
        # Note: version=2 means the integer seed uses all the bytes in _beta
        random.seed(a=self._beta, version=2)

    def generate(self, model="tinykeep"):

        self.model = self.import_model(model)
        self.model.generate(self)

    def import_model(self, model):
        try:
            module = f".generators.{model}.model"
            return importlib.import_module(module, __package__).Generator(
                debug=self.args.debug
            )
        except ImportError:
            raise Error(
                f"failed to import model using: {module} relative to {__package__}"
            )

    def tojson(self, dumps=True):

        map = dict(
            gp=self._gp,
            vrf_inputs=self.vrf_inputs(format=None),
            model_type=self.model.NAME,
            model=self.model.tojson(),
        )

        if not dumps:
            return map

        return json.dumps(map)

    def load_common(self, source):

        if isinstance(source, str):
            map = json.loads(source)
        else:
            map = json.load(source)

        self._gp = map["gp"]
        self._seed = bytes.fromhex(map["vrf_inputs"]["seed"])
        self._pi = bytes.fromhex(map["vrf_inputs"]["pi"])
        self._beta = bytes.fromhex(map["vrf_inputs"]["beta"])
        self._public_key = bytes.fromhex(map["vrf_inputs"]["public_key"])
        self._alpha = map["vrf_inputs"]["alpha"].encode()

        # guarantee on load that the rng state is the same as it was at the
        # begining of generation.
        self.reseed_rng()

        return map

    def load_model(self, map):

        self.model = self.import_model(map["model_type"])
        self.model.fromjson(self, map["model"])

    def load(self, source):

        map = self.load_common(source)
        self.load_model(map)

    def render(self, svgfile):

        opts = self.model.create_render_opts(self.args)

        dwg = svgwrite.Drawing(filename=svgfile)
        arena = dwg.add(dwg.g(id="arena", fill="blue"))
        self.model.render(dwg, arena, opts=opts)
        dwg.save(pretty=True)

    def vrf_inputs(self, format="json"):

        vrf = dict(
            seed=self._seed.hex(),
            alpha=self._alpha.decode(),
            pi=self._pi.hex(),
            beta=self._beta.hex(),
            public_key=self._public_key.hex(),
        )
        if self._generated_secret:
            vrf["secret"] = self._secret.hex()
        if format == "json":
            return json.dumps(vrf, sort_keys=True, indent=2)
        return vrf


def run_generate(args):
    """Generate a map"""

    g = Map(args)

    if args.loadfile:
        f = open(args.loadfile, "r")
        g.load(f)
    else:
        g.generate()

    if args.savefile:
        with open(args.savefile, "w") as f:
            json.dump(g.tojson(dumps=False), f, sort_keys=True, indent=2)

    if args.svgfile is not None:
        g.render(args.svgfile)

    # box = rand_box(gp.arena_size, gp.arena_size, gp.room_szratio, gp.tile_snap_size)
    # a, b = rand_split_box(box)
    # visdbg_split_box(args.svgfile, g, box, a, b)
    return 0


def run(args=None):
    if args is None:
        args = sys.argv[1:]

    top = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    top.set_defaults(func=lambda a, b: print("See sub commands in help"))

    subcmd = top.add_subparsers(title="Availalbe commands")
    p = subcmd.add_parser("gen", help=run_generate.__doc__)
    p.set_defaults(func=run_generate)

    g_defaults = Map.defaults()
    p.add_argument(
        "--secret",
        "-k",
        default=None,
        help="""private key for the
    gnerator commitment. only the possesor of this key can prove they generated
    the map and with what parameters""",
    )
    p.add_argument(
        "--seed",
        "-s",
        default=None,
        help="seed for the RNG. By default, generated and printed",
    )

    p.add_argument("--gp-arena-size", type=float, default=g_defaults.gp_arena_size)
    p.add_argument(
        "--gp-corridor-redundancy",
        type=float,
        default=g_defaults.gp_corridor_redundancy,
    )
    p.add_argument("--gp-flock-factor", type=float, default=g_defaults.gp_flock_factor)
    p.add_argument(
        "--gp-main-room-thresh", type=float, default=g_defaults.gp_main_room_thresh
    )
    p.add_argument(
        "--gp-min-separation-factor",
        type=float,
        default=g_defaults.gp_min_separation_factor,
    )
    p.add_argument("--gp-model", default=g_defaults.gp_model)
    p.add_argument("--gp-room-szmax", type=float, default=g_defaults.gp_room_szmax)
    p.add_argument("--gp-room-szmin", type=float, default=g_defaults.gp_room_szmin)
    p.add_argument("--gp-room-szratio", type=float, default=g_defaults.gp_room_szratio)
    p.add_argument("--gp-rooms", default=g_defaults.gp_rooms)
    p.add_argument("--gp-tan-fudge", type=float, default=g_defaults.gp_tan_fudge)
    p.add_argument(
        "--gp-tile-snap-size", type=float, default=g_defaults.gp_tile_snap_size
    )
    p.add_argument("--loadfile", default=None)
    p.add_argument("--savefile", default=None)
    p.add_argument("--render-generations", type=int, default=-1)
    p.add_argument("--svgfile", default=None)
    p.add_argument("--debug", action="store_true")
    p.add_argument("--no-label-rooms", action="store_true")
    p.add_argument("--no-label-corridors", action="store_true")
    p.add_argument("--no-legend", action="store_true")

    args = top.parse_args(args)
    return args.func(args)


def main():
    return run_status(run)
