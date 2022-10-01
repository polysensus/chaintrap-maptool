import secrets
from enum import Enum

import uvicorn
from fastapi import FastAPI
from starlette.responses import Response
from fastapi.encoders import jsonable_encoder

from pydantic import BaseModel, Field

from maptool.map import Map, hash, gp_from_alphastr

class ModelName(str, Enum):
    tinykeep = "tinykeep"

class GeneratorInputs(BaseModel):
    model: ModelName = Field(
        default = "tinykeep", description="map generation algorithm name")
    arena_size: float = Field(
        default = 512 * 4.0, description="unit size of the map area to fill")
    corridor_redundancy: float = Field(
        default = 15.0,
        description="makes the map more interesting by allowing redundant connections")
    flock_factor: float = Field(
        default=600.0,
        description="""
            controls how keen are the rooms to spread out. to small and the map
            will fail to generate"""
    )
    main_room_thresh: float = Field(
        default = 0.8,
        descriptor="""
            controls the percentage of rooms that are part of the main
            routes""")
    min_separation_factor: float = Field(
        default = 1.7,
        description = """all rooms must be separated by this factor before the
        rooms are considered fully settled""")
    room_szmax: float = Field(
        default = 0,
        description = """maximum room size (width or height) if <=0 forced to
        arena_size / 2.0""")
    room_szmin: float = Field(
        default = 0,
        description = """minimum room size (width or height) if <=0 forced to
        arena_size / 4.0""")
    room_szratio: float = Field(
        default = 1.8,
        description = """controls the maximum difference between width and
        height (how skinny the rooms can be)""")
    rooms: float = Field(
        default = 16, description = """number of rooms to create"""
    )
    tan_fudge: float = Field(
        default = 0.0001,
        description = "geometry fudge, should not need to set this")
    tile_snap_size: float = Field(
        default = 4.0,
        description = """the room width and height are snapped to grid units of this size""")

class ProofRequest(BaseModel):
    gp: GeneratorInputs
    seed: str = Field(
        default=None,
        description="""random seed to combine with gp to grow the map. if not
        provided, it is generated randomly and returned""")

class ProofResponse(BaseModel):
    gp: GeneratorInputs
    secret: str
    public_key: str
    alpha: str
    hash_alpha: str
    beta: str
    pi: str


class GenerateRequest(BaseModel):
    public_key: str
    alpha: str
    beta: str
    pi: str


class XmlResponse(Response):
    media_type = "text/xthml"
    def render(self, content) -> bytes:
        return content.encode('utf-8')

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "The Root"}

@app.post("/commit/", response_model=ProofResponse)
async def commit(req: ProofRequest):

    if req.gp.room_szmin == 0:
        req.gp.room_szmin = req.gp.arena_size / 4.0
    if req.gp.room_szmax == 0:
        req.gp.room_szmax = req.gp.arena_size / 2.0

    args = type('args', (), dict([('gp_' + k, v) for k, v in req.gp.dict().items()]))
    args.seed = req.seed
    args.secret = None

    map = Map.from_args(args)
    vrf_inputs = map.vrf_inputs(format=None)
    res = ProofResponse(
        gp = req.gp,
        seed = vrf_inputs['seed'],
        alpha = vrf_inputs['alpha'],
        hash_alpha = f"sha512:0x{hash(vrf_inputs['alpha'].encode()).hex()}",
        pi = vrf_inputs['proof']['pi'],
        beta = vrf_inputs['proof']['beta'],
        secret = vrf_inputs['secret'],
        public_key = vrf_inputs['proof']['public_key']
    )

    return res

@app.post("/generate/")
async def generate(req: GenerateRequest, svg: bool = False):

    vrf_inputs = dict(
        public_key = req.public_key,
        alpha = req.alpha,
        proof = dict(
            beta = req.beta,
            pi = req.pi
        )
    )

    map = Map(None)
    map.set_vrf_inputs(vrf_inputs)
    map.generate()
    if not svg:
        return map.tojson(dumps=False)
    return XmlResponse(map.render(None))

@app.get("/defaults")
async def defaults():
    return dict(gp = dict(
        [
            (k[k.startswith('gp_') and len('gp_'):], v)
            for k, v in Map.defaults_dict().items()
            if v is not None
        ]
    ))


@app.get("/healthz")
async def healthz():
    return {"status": "ready"}


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)
