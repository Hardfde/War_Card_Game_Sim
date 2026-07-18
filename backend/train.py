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
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix

from simulation import simulation
from features_model import extract, N_FEATURES, FEATURE_NAMES
from features_partial import (
    extract as extract_partial,
    N_FEATURES as N_FEATURES_PARTIAL,
    FEATURE_NAMES as FEATURE_NAMES_PARTIAL,
)

MODELS_DIR = Path("models")
MODELS_DIR.mkdir(exist_ok=True)
np.seterr(all="ignore")


def generate_data(n_games: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    deck = simulation.build_deck()
    total_cards = len(deck)

    X, y, X_p, y_p = [], [], [], []
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
            X_p.append(extract_partial(result.snapshots, total_cards, i))
            y.append(label)
            y_p.append(label)

        if (game_num + 1) % 1000 == 0:
            print(f"  {game_num + 1}/{n_games} games | {draws} draws | {time.time() - start:.1f}s")

    return (
        np.array(X, dtype=np.float32),
        np.array(y, dtype=np.float32),
        np.array(X_p, dtype=np.float32),
        np.array(y_p, dtype=np.float32),
    )


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


def evaluate(model, X_test, y_test, feature_names: list[str]):
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    cm = confusion_matrix(y_test, preds)

    print(f"  Test Accuracy: {acc * 100:.2f}%")
    print(f"  Confusion Matrix:")
    print(f"    {cm[0][0]} (True Neg) | {cm[0][1]} (False Pos)")
    print(f"    {cm[1][0]} (False Neg) | {cm[1][1]} (True Pos)")

    clf_step = model.named_steps.get("clf")
    if isinstance(clf_step, LogisticRegression):
        print(f"  Coefficients:")
        for name, coef in zip(feature_names, clf_step.coef_[0]):
            print(f"    {name}: {coef:.4f}")

    return acc, cm


def train_and_save(X, y, feature_names, suffix, models_to_train, cv):
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    models = build_models()

    for name in models_to_train:
        print(f"\nTraining {name}{suffix}...")
        model = models[name]

        if cv:
            scores = cross_val_score(model, X_train, y_train, cv=5, scoring="roc_auc", n_jobs=-1)
            print(f"  CV ROC-AUC: {scores.mean():.4f} +/- {scores.std():.4f}")

        model.fit(X_train, y_train)
        evaluate(model, X_test, y_test, feature_names)

        path = MODELS_DIR / f"war_{name}{suffix}.pkl"
        joblib.dump(model, path)
        print(f"  Saved to {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=10_000)
    parser.add_argument("--cv", action="store_true")
    args = parser.parse_args()

    print(f"Generating data: {args.games} games")
    X, y, X_p, y_p = generate_data(args.games)

    assert X.shape[1] == N_FEATURES, f"Feature mismatch: got {X.shape[1]}, expected {N_FEATURES}"
    assert X_p.shape[1] == N_FEATURES_PARTIAL, f"Feature mismatch: got {X_p.shape[1]}, expected {N_FEATURES_PARTIAL}"

    print(f"Full info dataset:    {X.shape[0]:,} samples | P1 win rate: {y.mean():.3f}")
    print(f"Partial info dataset: {X_p.shape[0]:,} samples | P1 win rate: {y_p.mean():.3f}")

    to_train = ["logistic", "boosted"]

    train_and_save(X, y, FEATURE_NAMES, "", to_train, args.cv)
    train_and_save(X_p, y_p, FEATURE_NAMES_PARTIAL, "_partial", to_train, args.cv)

    meta = {
        "models":       to_train,
        "n_games":      args.games,
        "n_features":   N_FEATURES,
        "n_features_partial": N_FEATURES_PARTIAL,
        "feature_names": FEATURE_NAMES,
        "feature_names_partial": FEATURE_NAMES_PARTIAL,
        "total_cards":  52,
        "trained_at":   time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with open(MODELS_DIR / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    print(f"\nMetadata saved.")


if __name__ == "__main__":
    main()