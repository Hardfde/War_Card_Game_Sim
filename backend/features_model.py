# features_model.py

import numpy as np
from simulation import MAX_TURNS
RECENT_N   = 10     # window for recent win rate
HIGH_CARD  = 11     # jack and above (with ace = 14)
N_FEATURES = 11      # sanity check constant


def extract(snapshots: list[dict], total_cards: int, index: int = -1) -> np.ndarray:
    """
    Takes the full snapshot history and returns a flat feature vector.
    All values normalised to roughly [0, 1].

    NOTE: full information version — uses actual hand contents.
    Will be replaced with partial information version later.
    """
    history = snapshots[:index + 1] if index != -1 else snapshots
    current = history[-1]

    # ------------------------------------------------------------------
    # 1. Card count
    #    Single value — p2's share is always 1 - p1_share so redundant.
    # ------------------------------------------------------------------

    p1_share = len(current["p1_cards"]) / total_cards

    # ------------------------------------------------------------------
    # 2. Average rank of each player's current hand
    #    Normalised over max rank (14 = ace).
    #    Tells the model who is holding the stronger cards right now.
    # ------------------------------------------------------------------

    p1_hand = current["p1_cards"]
    p2_hand = current["p2_cards"]

    p1_avg_rank = (sum(p1_hand) / len(p1_hand) / 14) if p1_hand else 0.5
    p2_avg_rank = (sum(p2_hand) / len(p2_hand) / 14) if p2_hand else 0.5

    # ------------------------------------------------------------------
    # 3. High card share
    #    Fraction of each player's hand that is jack or above (incl ace).
    #    Normalised implicitly — already a fraction in [0, 1].
    # ------------------------------------------------------------------

    p1_high = sum(1 for r in p1_hand if r >= HIGH_CARD) / len(p1_hand) if p1_hand else 0.5
    p2_high = sum(1 for r in p2_hand if r >= HIGH_CARD) / len(p2_hand) if p2_hand else 0.5

    # ------------------------------------------------------------------
    # 4. Win streak
    #    Number of consecutive non-war battles P1 won coming INTO the
    #    current snapshot (counting the current battle).
    #    Normalised softly by RECENT_N — can exceed 1.0 for long streaks.
    # ------------------------------------------------------------------

    streak = 0
    for s in reversed(history):    # exclude current snapshot
        if s["p1_won"]:
            streak += 1
        else:
            break

    norm_streak = min(streak / RECENT_N, 1)

    # ------------------------------------------------------------------
    # 5. Recent win rate
    #    P1's win rate over the last RECENT_N battles.
    #    More sensitive to momentum than all-time win rate.
    # ------------------------------------------------------------------

    recent = history[-RECENT_N:]
    p1_recent_win_rate = sum(1 for s in recent if s["p1_won"]) / len(recent)

    # ------------------------------------------------------------------
    # 6. Average win margin
    #    Mean rank difference of deciding cards across all battles.
    #    Normalised over max possible margin (14 - 2 = 12).
    #    Default 0.5 — neutral assumption, not "no margin".
    # ------------------------------------------------------------------

    margins = [s["margin"] for s in history]
    avg_margin = (sum(margins) / len(margins) / 12) if margins else 0.5
    curr_margin = current["margin"] / 12
    # ------------------------------------------------------------------
    # 7. Game state
    #    norm_turn: how far through the max turn limit we are.
    #    war_rate:  fraction of battles that involved a war — captures
    #               how collision-prone this deck ordering is.
    # ------------------------------------------------------------------

    total_turns = len(history)
    wars        = sum(1 for s in history if s["was_war"])

    norm_turn = min(total_turns / MAX_TURNS, 1.0)
    war_rate  = wars / total_turns   # total_turns always >= 1

    # ------------------------------------------------------------------
    # Assemble
    # ------------------------------------------------------------------

    vector = np.array([
        p1_share,           # 0  card count
        p1_avg_rank,        # 1  p1 average rank
        p2_avg_rank,        # 2  p2 average rank
        p1_high,            # 3  p1 high card fraction
        p2_high,            # 4  p2 high card fraction
        norm_streak,        # 5  p1 win streak
        p1_recent_win_rate, # 6  p1 recent win rate
        avg_margin,         # 7  average deciding margin
        curr_margin,        # 8  current win margin
        norm_turn,          # 9  game age
        war_rate,           # 10 war frequency
    ], dtype=np.float32)

    assert len(vector) == N_FEATURES, f"Expected {N_FEATURES} features, got {len(vector)}"

    return vector