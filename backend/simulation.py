from collections import deque
from dataclasses import dataclass
from multiprocessing import pool
import random


@dataclass
class GameResult:
    outcome: int          # 1 = P1 wins, -1 = P2 wins, 0 = draw
    turns: int
    wars: int
    snapshots: list[tuple[int,int]]       # list of dicts with state at each turn



MAX_TURNS = 5000

class simulation:

    def __init__(self, set_1: list[int], set_2 : list[int]):
        self.set_1 = set_1
        self.set_2 = set_2
        self.step = 0
        self.wars = 0
        self.stop = False


    def simulate(self) -> GameResult:
        q1 = deque(self.set_1)
        q2 = deque(self.set_2)
        snapshots = []
        while q1 and q2 and self.step < MAX_TURNS and not self.stop:
            self.battle(q1, q2)
            snapshots.append((len(q1), len(q2)))
        if q1 and not q2:
            outcome = 1
        elif q2 and not q1:
            outcome = -1
        else:
            outcome = 0
        return GameResult(outcome = outcome, turns = self.step, wars = self.wars, snapshots = snapshots)


    def battle(self, q1 : deque, q2 : deque, c1_war : list = None, c2_war : list = None) -> bool:
        self.step += 1
        c1 = q1.popleft()
        c2 = q2.popleft()

        pending1 = (c1_war or []) + [c1]
        pending2 = (c2_war or []) + [c2]

        if c1 > c2:
            q1.extend(pending1)
            q1.extend(pending2)
            return True
        elif c1 < c2:
            q2.extend(pending1)
            q2.extend(pending2)
            return False
        
        self.wars += 1
        if len(q1) < 3 and len(q2) < 3:
            self.stop = True
            return None
        elif len(q1) < 3:
            q2.extend(pending2)
            q2.extend(pending1)
            q2.extend(q1)
            q1.clear()
            return False
        elif len(q2) < 3:
            q1.extend(pending1)
            q1.extend(pending2)
            q1.extend(q2)
            q2.clear()
            return True

        for _ in range(3):
            pending1.append(q1.popleft())
            pending2.append(q2.popleft())
        return self.battle(q1, q2, pending1, pending2)
    
    def build_deck() -> list[int]:
        return[rank for rank in range(1,14) for _ in range(4)]
    
    def deal(deck: list[int]) -> tuple[list[int], list[int]]:
        shuffled = deck.copy()
        random.shuffle(shuffled)
        return shuffled[:26], shuffled[26:]

if __name__ == "__main__":
    countWins = 0
    countLoses = 0
    countDraws = 0
    trials = 100000
    steps = 0
    maxSteps = 0
    stopCount = 0
    for i in range(trials):
        pool = [1,2,3] * 4
        random.shuffle(pool)
        set_1 = pool[:6]
        set_2 = pool[6:12]
        # set_1 = [1,4,2,1,2,3]
        # set_2 = [4,4,4,1,3,2]

        sim = simulation(set_1, set_2)
        temp = sim.simulate()
        if sim.step >= 25000:
            stopCount += 1
        else:
            steps += sim.step
        if sim.step > maxSteps and sim.step < 25000:
            maxSteps = sim.step
        if temp == 1:
            countWins += 1
        elif temp == -1:
            countLoses += 1
        else:
            countDraws += 1
  
    print(f"Win percentage: {(countWins/ (countWins + countLoses + countDraws)) * 100:.2f}%")
    print(f"Lose percentage: {(countLoses/ (countWins + countLoses + countDraws)) * 100:.2f}%")
    print(f"Draw percentage: {(countDraws/ (countWins + countLoses + countDraws)) * 100:.2f}%")
    print(f"Average steps: {steps / (trials - stopCount):.2f}")
    print(f"Maximum steps: {maxSteps}")
    print(f"Stopped games: {stopCount}")