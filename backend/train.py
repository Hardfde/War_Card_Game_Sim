# train.py

import argparse
import json
import time
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score

from simulation import simulation
from features_model import extract, N_FEATURES


MODELS_DIR = Path("models")
MODELS_DIR.mkdir(exist_ok=True)


def generate_data(n_games: int) -> tuple[np.ndarray, np.ndarray]:
    deck = simulation.build_deck()
    total_cards = len(deck)

    X, y = [], []
    draws = 0
    start = time.time()

    for game_num in range(n_games):
        hand1, hand2 = simulation.deal(deck)
        result = simulation(hand1, hand2).simulate()

        if result.outcome == 0:
            draws += 1
            continue

        label = 1 if result.outcome == 1 else 0

        for i in range(len(result.snapshots)):
            X.append(extract(result.snapshots, total_cards, i))
            y.append(label)

        if (game_num + 1) % 1000 == 0:
            print(f"  {game_num + 1}/{n_games} games | {draws} draws | {time.time() - start:.1f}s")

    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


def build_models() -> dict:
    return {
        "logistic": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000)),
        ]),
        "boosted": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", GradientBoostingClassifier(n_estimators=100)),
        ]),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=10_000)
    parser.add_argument("--model", choices=["logistic", "boosted", "both"], default="both")
    parser.add_argument("--cv", action="store_true")
    args = parser.parse_args()

    print(f"Generating data: {args.games} games")
    X, y = generate_data(args.games)

    print(f"Dataset: {X.shape[0]:,} samples | P1 win rate: {y.mean():.3f}")

    assert X.shape[1] == N_FEATURES, f"Feature mismatch: got {X.shape[1]}, expected {N_FEATURES}"

    models = build_models()
    to_train = ["logistic", "boosted"] if args.model == "both" else [args.model]

    for name in to_train:
        print(f"\nTraining {name}...")
        model = models[name]

        if args.cv:
            scores = cross_val_score(model, X, y, cv=5, scoring="roc_auc", n_jobs=-1)
            print(f"  CV ROC-AUC: {scores.mean():.4f} +/- {scores.std():.4f}")

        model.fit(X, y)

        path = MODELS_DIR / f"war_{name}.pkl"
        joblib.dump(model, path)
        print(f"  Saved to {path}")

    meta = {
        "models":       to_train,
        "n_games":      args.games,
        "n_features":   N_FEATURES,
        "total_cards":  52,
        "trained_at":   time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with open(MODELS_DIR / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    print(f"\nMetadata saved.")


if __name__ == "__main__":
    main()