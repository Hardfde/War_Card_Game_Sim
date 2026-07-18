from collections import deque
from dataclasses import dataclass
import random


@dataclass
class GameResult:
    outcome: int          # 1 = P1 wins, -1 = P2 wins, 0 = draw
    turns: int
    wars: int
    snapshots: list[dict]       # list of dicts with state at each turn



MAX_TURNS = 5000

class simulation:

    def __init__(self, set_1: list[int], set_2 : list[int]):
        self.q1 = deque((v, False) for v in set_1)
        self.q2 = deque((v, False) for v in set_2)
        self.step = 0
        self.wars = 0
        self.stop = False


    def simulate(self) -> GameResult:
        snapshots = []
        while self.q1 and self.q2 and self.step < MAX_TURNS and not self.stop:
            snapshot = self.battle(self.q1,self.q2)
            if snapshot is not None:
                snapshots.append(snapshot)
        if self.q1 and not self.q2:
            outcome = 1
        elif self.q2 and not self.q1:
            outcome = -1
        else:
            outcome = 0
        return GameResult(outcome = outcome, turns = self.step, wars = self.wars, snapshots = snapshots)


    def battle(self, q1 : deque, q2 : deque, c1_war : list = None, c2_war : list = None) -> dict:
        self.step += 1
        raw_c1 = q1.popleft()
        raw_c2 = q2.popleft()
        c1 = (raw_c1[0], True)
        c2 = (raw_c2[0], True)

        pending1 = (c1_war or []) + [c1]
        pending2 = (c2_war or []) + [c2]

        if c1[0] > c2[0]:
            q1.extend(pending1)
            q1.extend(pending2)
            return self._make_snapshot(q1, q2, pending1, pending2, p1_won=True)
        elif c1[0] < c2[0]:
            q2.extend(pending2)
            q2.extend(pending1)
            return self._make_snapshot(q1, q2, pending1, pending2, p1_won=False)
        
        self.wars += 1
        if len(q1) < 4 and len(q2) < 4:
            self.stop = True
            return None
        elif len(q1) < 4:
            q2.extend(pending2)
            q2.extend(pending1)
            q2.extend(q1)
            q1.clear()
            return self._make_snapshot(q1, q2, pending1, pending2, p1_won=False)
        elif len(q2) < 4:
            q1.extend(pending1)
            q1.extend(pending2)
            q1.extend(q2)
            q2.clear()
            return self._make_snapshot(q1, q2, pending1, pending2, p1_won=True)

        for _ in range(3):
            pending1.append(q1.popleft())
            pending2.append(q2.popleft())
        return self.battle(q1, q2, pending1, pending2)
    
    def _make_snapshot(self, q1, q2, pending1, pending2, p1_won: bool) -> dict:
        # pending[-1] is always the deciding (or forfeit) card's value
        deciding_c1 = pending1[-1][0]
        deciding_c2 = pending2[-1][0]
 
        # number of war levels this battle went through
        # each war level adds exactly 4 cards to pending (3 face-down + 1 decider)
        # plus the original tie card at index 0, so:
        n_wars = (len(pending1) - 1) // 4
 
        return {
            "p1_cards": list(q1),          # list of (value, seen) pairs
            "p2_cards": list(q2),
            "p1_card_played": deciding_c1,
            "p2_card_played": deciding_c2,
            "p1_won": p1_won,
            "margin": (deciding_c1 - deciding_c2) if p1_won else (deciding_c2 - deciding_c1),
            "was_war": n_wars > 0,
            "n_wars": n_wars,
        }
    
    @staticmethod
    def build_deck() -> list[int]:
        return[rank for rank in range(2,15) for _ in range(4)]
    
    @staticmethod
    def deal(deck: list[int]) -> tuple[list[int], list[int]]:
        shuffled = deck.copy()
        random.shuffle(shuffled)
        return shuffled[:26], shuffled[26:]