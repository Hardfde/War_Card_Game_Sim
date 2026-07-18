from pathlib import Path
import json

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
from typing import Optional

from simulation import simulation
from features_model import extract, N_FEATURES


# ------------------------------------------------------------------
# App
# ------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    # runs on startup
    load_models()
    yield


app = FastAPI(
    title="War Card Game API",
    description="Win probability estimation for the War card game",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://[::]:3000"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

MODELS_DIR = Path(__file__).parent / "models"
_models: dict = {}
_meta:   dict = {}


def load_models():
    global _models, _meta

    meta_path = MODELS_DIR / "meta.json"
    if meta_path.exists():
        with open(meta_path) as f:
            _meta = json.load(f)

    for name in ["logistic", "boosted", "logistic_partial", "boosted_partial"]:
        path = MODELS_DIR / f"war_{name}.pkl"
        if path.exists():
            _models[name] = joblib.load(path)
            print(f"Loaded {name} model")

    if not _models:
        print("WARNING: no models found — run train.py first")

_game: Optional[dict] = None


def _require_game():
    if _game is None:
        raise HTTPException(status_code=404, detail="No active game — call /game/new first")


def _require_game_active():
    _require_game()
    if _game["over"]:
        raise HTTPException(status_code=403, detail="Game is over — call /game/new to start a new one")


def _get_model(name: str):
    if name not in _models:
        raise HTTPException(status_code=503, detail=f"Model '{name}' not loaded. Run train.py first.")
    return _models[name]


class StepRequest(BaseModel):
    c1: int = Field(..., ge=2, le=14)
    c2: int = Field(..., ge=2, le=14)
    model: str = Field("boosted") # changed to boosted


class StepResponse(BaseModel):
    p1_win_prob: float


class NewGameResponse(BaseModel):
    q1: list[int]
    q2: list[int]


class StateResponse(BaseModel):
    p1_cards: int
    p2_cards: int
    turns:    int
    wars:     int


# Endpoints

@app.get("/health")
def health():
    return {
        "status": "ok",
        "models_loaded": list(_models.keys()),
        "game_active": _game is not None and not _game["over"],
    }


class NewGameRequest(BaseModel):
    q1: list[int] = Field(..., min_length=1)
    q2: list[int] = Field(..., min_length=1)

@app.post("/game/new", response_model=NewGameResponse)
def new_game(req: NewGameRequest):
    global _game

    _game = {
        "sim":       simulation(req.q1, req.q2),
        "snapshots": [],
        "over":      False,
    }

    return NewGameResponse(q1=req.q1, q2=req.q2)


@app.post("/game/step", response_model=StepResponse)
def step(req: StepRequest):
    global _game
    _require_game_active()

    model = _get_model(req.model)

    # validate frontend and backend agree on what cards are at the top
    if req.c1 != _game["sim"].q1[0][0] or req.c2 != _game["sim"].q2[0][0]:
        raise HTTPException(status_code=409, detail="Frontend and backend deques are out of sync")

    snapshot = _game["sim"].battle(_game["sim"].q1, _game["sim"].q2)

    if snapshot is not None:
        _game["snapshots"].append(snapshot)

    if _game["sim"].stop:
        _game["over"] = True

    # compute features from full snapshot history
    feats = extract(_game["snapshots"], total_cards=52)
    assert len(feats) == N_FEATURES

    prob = float(model.predict_proba(feats.reshape(1, -1))[0][1])

    return StepResponse(p1_win_prob=round(prob, 4))



@app.get("/game/state", response_model=StateResponse)
def game_state():
    _require_game()
    sim = _game["sim"]
    return StateResponse(
        p1_cards=len(sim.q1),
        p2_cards=len(sim.q2),
        turns=sim.step,
        wars=sim.wars,
    )


@app.post("/game/end")
def end_game():
    global _game
    _require_game()
    _game = None