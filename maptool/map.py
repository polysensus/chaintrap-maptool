"""map generation"""
import sys
import io
import argparse
import secrets
import json
import random
import hashlib
import pickle
import importlib
from pathlib import Path
import svgwrite
import vrf.ec
from vrf.ec import ecvrf_prove, ecvrf_proof_to_hash
from .clicommon import run_status

def hash(message):
    """Return 64-byte SHA512 hash of arbitrary-length byte message"""
    return hashlib.sha512(message).digest()


def gp_from_alphastr(alphastr: str) -> dict:
    items = alphastr.split(":")[3].split(',')
    gp = {}
    for it in items:
        it = it.split('=')
        for ty in [int, float]:
            try:
                gp[it[0]] = ty(it[1])
                break
            except ValueError:
                continue
        else:
            gp[it[0]] = it[1]

    return gp


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
    def defaults_dict(cls):
        return dict(
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
        )

    @classmethod
    def defaults(cls):
        return type(
            "MapArgs",
            (),
            cls.defaults_dict()
        )

    def __init__(self, args):

        self.args = args
        if self.args is None:
            self.args = self.defaults()

    def canonical_gpstr(self, gp) -> str:
        """
        Convert the provided generation paramaters to a string in a cannonical
        way.
        """
        gp = [f"{k}={v}" for k, v in gp.items()]
        gp.sort()
        return ",".join(gp)

    def _gp_from_alphastr(self, alphastr: str) -> dict:
        return gp_from_alphastr(alphastr)


    def cannonical_alpha(self, gpstr: str, seed: bytes) -> str:
        """Make the vrf alpha input from the seed and the generation parameter string"""

        if not isinstance(gpstr, str):
            raise ValueError(f"gpstr must be string here, call cannonical_gp2str to get one")

        return f"{self._version}:{self._variant}:{seed.hex()}:{gpstr}"

    def _seed_from_alphastr(self, alphastr: str) -> bytes:
        return bytes.fromhex(alphastr.split(":", 3)[2])

    def make_commitment(self, gp: dict, seed: bytes, secret: bytes):
        """Commit to the map, requires the caller to reveal the secret key

        Note: We factor this class so that the commitment can be made off line
        and independently. We can store this generator in a docker image.
        Possibly in ipfs. 

        Alternately, we can host it as a service and generate the secret key for
        the caller. It would then be returned with the map - but we don't store
        it ourselves. Its then like an api key - they need to save it to later
        prove the map.

        Only the holder of the secret can prove
        a) they generated the map
        b) what the map generation inputs were
        """

        gpstr = self.canonical_gpstr(gp)
        alpha = self.cannonical_alpha(gpstr, seed)
        public_key = vrf.ec.get_public_key(secret)
        p_status, pi = ecvrf_prove(secret, alpha.encode())
        if p_status != "VALID":
            raise SeedError("failed to generate seed and paramaters proof")

        b_status, beta = ecvrf_proof_to_hash(pi)
        if b_status != "VALID":
            raise SeedError("failed to derive hash from seed proof")

        return (alpha, dict(
            public_key=public_key.hex(),
            pi=pi.hex(),
            beta=beta.hex()
        ))

    @classmethod
    def from_file(cls, args):
        map = Map(args)
        f = open(args.loadfile, "r")
        map.load(f)
        return map
    
    @classmethod
    def from_source(cls, args, source):
        map = Map(args)
        map.load(source)
        return map


    @classmethod
    def from_args(cls, args):
        """
        """
        map = cls(args)
        map.new_proof()

        return map

    def new_proof(self):

        # If the user provided a private key, use it. Otherwise generate one
        secret = self.args.secret
        if secret is not None:
            secret = bytes.fromhex(secret)
        if secret is None:
            secret = secrets.token_bytes(nbytes=32)

        # If the user provided a seed, use it. Otherwise generate one
        seed = self.args.seed
        if seed is not None:
            seed = bytes.fromhex(seed)
        if seed is None:
            seed = secrets.token_bytes(nbytes=8)

        gp = dict()
        for k, v in self.args.__dict__.items():
            if k.startswith("gp_"):
                gp[k[3:]] = v

        alpha, proof = self.make_commitment(gp, seed, secret)
        vrf_inputs = dict(alpha=alpha, proof=proof)
        if self.args.secret is None:
            vrf_inputs['secret'] = secret.hex()

        if self.args.seed is None:
            vrf_inputs['seed'] = seed.hex()

        self.set_vrf_inputs(vrf_inputs)


    def set_vrf_inputs(self, vrf_inputs):
        """Set the map rng based on the vrv provable state"""

        self._vrf_inputs = vrf_inputs.copy()
        self._proof = vrf_inputs['proof'].copy()
        self._pi = bytes.fromhex(self._proof['pi'])
        self._beta = bytes.fromhex(self._proof['beta'])
        self.reseed_rng(hash(self._vrf_inputs["alpha"].encode()))

        self._gp = self._gp_from_alphastr(self._vrf_inputs["alpha"])


    @property
    def gp(self):
        return type("GenerationParams", (), self._gp)

    def reseed_rng(self, hash_alpha = None):
        """Re seed the rng so the geneartor can run again with the current parameters"""
        if hash_alpha is not None:
            self._hash_alpha = hash_alpha
        # Note: version=2 means the integer seed uses all the bytes in _beta
        # XXXX: XXXX: this needs to seed on ALPHA! we put beta on the chain
        random.seed(a=self._hash_alpha, version=2)

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

    def load_common(self, source):

        if isinstance(source, str):
            map = json.loads(source)
        else:
            map = json.load(source)

        self._vrf_inputs = map["vrf_inputs"]
        self._gp = self._gp_from_alphastr(self._vrf_inputs["alpha"])
        self._beta = bytes.fromhex(self._vrf_inputs["proof"]["beta"])

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
        if svgfile is not None:
            dwg.save(pretty=True)
        else:
            return dwg.tostring()

    def vrf_inputs(self, format="json"):

        if not self._vrf_inputs:
            return {}

        if format == "json":
            return json.dumps(self._vrf_inputs, sort_keys=True, indent=2)
        return self._vrf_inputs.copy()

    def tojson(self, dumps=True):

        map = dict(
            vrf_inputs=self.vrf_inputs(format=None),
            model_type=self.model.NAME,
            model=self.model.tojson(),
        )

        if not dumps:
            return map

        return json.dumps(map)


def run_generate(args):
    """Generate a map"""

    if args.loadfile:
        g = Map.from_file(args)
    else:
        g = Map.from_args(args)
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
