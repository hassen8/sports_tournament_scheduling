# source/SAT/sat_z3_sb.py
#
# Z3-based SAT-style decision model WITH symmetry breaking.
# Same encoding as sat_z3.py, plus:
#   Week 1 is fixed to (1,2), (3,4), ..., in periods 1,2,...
#
# Output key: "SAT_Z3_SB_n"

import sys
import time
from itertools import combinations
from pathlib import Path
from z3 import Solver, Bool, Or, Not, AtLeast, AtMost, sat

sys.path.append(str(Path(__file__).resolve().parents[1]))
from common.io_json import write_result_json


def build_sat_model_z3_sb(n):
    periods = n // 2
    weeks = n - 1

    s = Solver()
    s.set("timeout", 300000)

    M = {}

    def M_var(i, j, p, w):
        key = (i, j, p, w)
        if key not in M:
            M[key] = Bool(f"M_{i}_{j}_{p}_{w}")
        return M[key]

    def exactly_one(lits):
        if len(lits) == 1:
            s.add(lits[0])
        elif len(lits) > 1:
            s.add(AtLeast(*lits, 1))
            s.add(AtMost(*lits, 1))

    def at_most_two(lits):
        if len(lits) > 2:
            s.add(AtMost(*lits, 2))

    teams = list(range(1, n + 1))
    pairs = list(combinations(teams, 2))

    # Slot
    for p in range(1, periods + 1):
        for w in range(1, weeks + 1):
            lits = [M_var(i, j, p, w) for (i, j) in pairs]
            exactly_one(lits)

    # Pair
    for (i, j) in pairs:
        lits = [M_var(i, j, p, w)
                for p in range(1, periods + 1)
                for w in range(1, weeks + 1)]
        exactly_one(lits)

    # Weekly
    for t in teams:
        for w in range(1, weeks + 1):
            week_lits = []
            for (i, j) in pairs:
                if t == i or t == j:
                    for p in range(1, periods + 1):
                        week_lits.append(M_var(i, j, p, w))
            exactly_one(week_lits)

    # Period
    for t in teams:
        for p in range(1, periods + 1):
            appearances = []
            for w in range(1, weeks + 1):
                for (i, j) in pairs:
                    if t == i or t == j:
                        appearances.append(M_var(i, j, p, w))
            at_most_two(appearances)

    # Symmetry breaking: fix week 1 pairings
    # Period k, week 1: match (2k-1, 2k)
    for k in range(1, periods + 1):
        i = 2*k - 1
        j = 2*k
        s.add(M_var(i, j, k, 1))

    return s, M


def extract_schedule(model, n, M):
    periods = n // 2
    weeks = n - 1
    sol = [[None for _ in range(weeks)] for _ in range(periods)]
    teams = range(1, n + 1)

    for p in range(1, periods + 1):
        for w in range(1, weeks + 1):
            for (i, j) in combinations(teams, 2):
                if model.eval(M[(i, j, p, w)], model_completion=True):
                    sol[p-1][w-1] = [i, j]
                    break
    return sol


def solve_sat_z3_sb(n):
    s, M = build_sat_model_z3_sb(n)
    start = time.time()
    res = s.check()
    elapsed = time.time() - start

    if res != sat:
        return None, elapsed, M

    return s.model(), elapsed, M


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python sat_z3_sb.py <n>")
        sys.exit(1)

    n = int(sys.argv[1])
    model, t, M = solve_sat_z3_sb(n)
    optimal = model is not None

    sol = extract_schedule(model, n, M) if optimal else []

    out_path = f"res/SAT/{n}.json"
    write_result_json("SAT_Z3_SB", n, out_path, t, optimal, sol)

    print(f"[SAT_Z3_SB] n={n} solved in {t:.3f}s → {out_path}")
