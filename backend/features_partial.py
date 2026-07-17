# features_partial.py

import numpy as np

RECENT_N   = 10
HIGH_CARD  = 11
MAX_TURNS  = 5000
N_FEATURES = 15

FEATURE_NAMES = [
    "p1_share",
    "p1_seen_fraction",
    "p2_seen_fraction",
    "p1_avg_rank_seen",
    "p2_avg_rank_seen",
    "p1_high_fraction_seen",
    "p2_high_fraction_seen",
    "p1_high_amount",
    "p2_high_amount",
    "norm_streak",
    "p1_recent_win_rate",
    "avg_margin",
    "curr_margin",
    "norm_turn",
    "war_rate",
]

# max possible high cards in the deck — J, Q, K, A = 4 ranks x 4 copies = 16
MAX_HIGH_CARDS = 16


def extract(snapshots: list[dict], total_cards: int, index: int = -1) -> np.ndarray:
    """
    Partial information feature extraction.

    Unlike features_model.py, hand contents here are lists of (value, seen)
    pairs. Only cards with seen=True are used for rank/high-card stats —
    this reflects what a player watching the game would actually know,
    since face-down war cards never get revealed even after they cycle
    back into play.

    index: same convention as features_model.py — slices snapshots[:index+1]
    if provided, otherwise uses the full list as-is.
    """

    history = snapshots[:index + 1] if index != -1 else snapshots
    current = history[-1]

    p1_hand = current["p1_cards"]   # list of (value, seen) pairs
    p2_hand = current["p2_cards"]

    # ------------------------------------------------------------------
    # 1. Card count
    # ------------------------------------------------------------------

    p1_share = len(p1_hand) / total_cards

    # ------------------------------------------------------------------
    # 2. Seen fraction — how much of each hand's contents are known
    # ------------------------------------------------------------------

    p1_seen_count = sum(1 for _, seen in p1_hand if seen)
    p2_seen_count = sum(1 for _, seen in p2_hand if seen)

    p1_seen_fraction = (p1_seen_count / len(p1_hand)) if p1_hand else 0.0
    p2_seen_fraction = (p2_seen_count / len(p2_hand)) if p2_hand else 0.0

    # ------------------------------------------------------------------
    # 3. Average rank of SEEN cards only
    # ------------------------------------------------------------------

    p1_seen_values = [v for v, seen in p1_hand if seen]
    p2_seen_values = [v for v, seen in p2_hand if seen]

    p1_avg_rank_seen = (sum(p1_seen_values) / len(p1_seen_values) / 14) if p1_seen_values else 0.5
    p2_avg_rank_seen = (sum(p2_seen_values) / len(p2_seen_values) / 14) if p2_seen_values else 0.5

    # ------------------------------------------------------------------
    # 4. High card fraction and count — SEEN cards only
    # ------------------------------------------------------------------

    p1_high_count_seen = sum(1 for v in p1_seen_values if v >= HIGH_CARD)
    p2_high_count_seen = sum(1 for v in p2_seen_values if v >= HIGH_CARD)

    p1_high_fraction_seen = (p1_high_count_seen / len(p1_seen_values)) if p1_seen_values else 0.5
    p2_high_fraction_seen = (p2_high_count_seen / len(p2_seen_values)) if p2_seen_values else 0.5

    # normalised by max possible high cards in the full deck —
    # alternative would be normalising by len(p1_seen_values); worth
    # testing both empirically to see which helps accuracy more
    p1_high_amount = p1_high_count_seen / MAX_HIGH_CARDS
    p2_high_amount = p2_high_count_seen / MAX_HIGH_CARDS

    # ------------------------------------------------------------------
    # 5. Win streak
    # ------------------------------------------------------------------

    streak = 0
    for s in reversed(history):
        if s["p1_won"]:
            streak += 1
        else:
            break

    norm_streak = min(streak / RECENT_N, 1.0)

    # ------------------------------------------------------------------
    # 6. Recent win rate
    # ------------------------------------------------------------------

    recent = history[-RECENT_N:]
    p1_recent_win_rate = sum(1 for s in recent if s["p1_won"]) / len(recent)

    # ------------------------------------------------------------------
    # 7. Margins — based on revealed deciding cards, always fully known
    # ------------------------------------------------------------------

    margins = [s["margin"] for s in history]
    avg_margin  = (sum(margins) / len(margins) / 12) if margins else 0.5
    curr_margin = current["margin"] / 12

    # ------------------------------------------------------------------
    # 8. Game state
    # ------------------------------------------------------------------

    total_turns = len(history)
    wars        = sum(1 for s in history if s["was_war"])

    norm_turn = min(total_turns / MAX_TURNS, 1.0)
    war_rate  = wars / total_turns

    # ------------------------------------------------------------------
    # Assemble — order must match FEATURE_NAMES above
    # ------------------------------------------------------------------

    vector = np.array([
        p1_share,                 # 0
        p1_seen_fraction,         # 1
        p2_seen_fraction,         # 2
        p1_avg_rank_seen,         # 3
        p2_avg_rank_seen,         # 4
        p1_high_fraction_seen,    # 5
        p2_high_fraction_seen,    # 6
        p1_high_amount,           # 7
        p2_high_amount,           # 8
        norm_streak,              # 9
        p1_recent_win_rate,       # 10
        avg_margin,                # 11
        curr_margin,               # 12
        norm_turn,                 # 13
        war_rate,                  # 14
    ], dtype=np.float32)

    assert len(vector) == N_FEATURES, f"Expected {N_FEATURES} features, got {len(vector)}"
    assert len(vector) == len(FEATURE_NAMES), "FEATURE_NAMES out of sync with vector"

    return vector