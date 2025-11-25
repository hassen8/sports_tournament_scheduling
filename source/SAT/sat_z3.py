# source/SAT/sat_z3.py
#
# Z3-based SAT-style decision model (no symmetry breaking).
# Match-based encoding:
#   M[i,j,p,w] = True  <=> match i(home) vs j(away) is in slot (p,w)
#
# Constraints:
#   1) Exactly 1 match per slot
#   2) Each pair meets exactly once
#   3) Each team plays exactly once per week
#   4) Each team appears at most twice per period
#
# We use Z3's AtLeast/AtMost for cardinalities instead of manually
# enumerating all pairs/triples, to avoid a combinatorial explosion.

import sys
import time
from itertools import combinations
from pathlib import Path
from z3 import Solver, Bool, Or, Not, AtLeast, AtMost, sat

sys.path.append(str(Path(__file__).resolve().parents[1]))
from common.io_json import write_result_json


def build_sat_model_z3(n):
    periods = n // 2
    weeks = n - 1

    s = Solver()
    s.set("timeout", 300000)  # 5 minutes

    M = {}

    def M_var(i, j, p, w):
        key = (i, j, p, w)
        if key not in M:
            M[key] = Bool(f"M_{i}_{j}_{p}_{w}")
        return M[key]

    def exactly_one(lits):
        # At least one and at most one true
        if len(lits) == 1:
            s.add(lits[0])
        elif len(lits) > 1:
            s.add(AtLeast(*lits, 1))
            s.add(AtMost(*lits, 1))

    def at_most_two(lits):
        if len(lits) > 2:
            s.add(AtMost(*lits, 2))
        # if len <= 2, it's automatically ≤2

    teams = list(range(1, n + 1))
    pairs = list(combinations(teams, 2))

    # 1) Slot constraint: each (p,w) has exactly one match
    for p in range(1, periods + 1):
        for w in range(1, weeks + 1):
            lits = [M_var(i, j, p, w) for (i, j) in pairs]
            exactly_one(lits)

    # 2) Pair constraint: each pair (i,j) meets exactly once
    for (i, j) in pairs:
        lits = [M_var(i, j, p, w)
                for p in range(1, periods + 1)
                for w in range(1, weeks + 1)]
        exactly_one(lits)

    # 3) Weekly: each team plays exactly once per week
    for t in teams:
        for w in range(1, weeks + 1):
            week_lits = []
            for (i, j) in pairs:
                if t == i or t == j:
                    for p in range(1, periods + 1):
                        week_lits.append(M_var(i, j, p, w))
            exactly_one(week_lits)

    # 4) Period: each team appears at most twice per period
    for t in teams:
        for p in range(1, periods + 1):
            appearances = []
            for w in range(1, weeks + 1):
                for (i, j) in pairs:
                    if t == i or t == j:
                        appearances.append(M_var(i, j, p, w))
            at_most_two(appearances)

    return s, M


def extract_schedule(model, n, M):
    periods = n // 2
    weeks = n - 1
    teams = list(range(1, n + 1))
    pairs = list(combinations(teams, 2))

    sol = [[None for _ in range(weeks)] for _ in range(periods)]

    for p in range(1, periods + 1):
        for w in range(1, weeks + 1):
            for (i, j) in pairs:
                if model.eval(M[(i, j, p, w)], model_completion=True):
                    sol[p - 1][w - 1] = [i, j]
                    break

    return sol


def solve_sat_z3(n):
    s, M = build_sat_model_z3(n)
    start = time.time()
    res = s.check()
    elapsed = time.time() - start

    if res != sat:
        return None, elapsed, M

    return s.model(), elapsed, M


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python sat_z3.py <n>")
        sys.exit(1)

    n = int(sys.argv[1])
    model, t, M = solve_sat_z3(n)
    optimal = model is not None

    sol = extract_schedule(model, n, M) if optimal else []

    out_path = f"res/SAT/{n}.json"
    write_result_json("SAT_Z3", n, out_path, t, optimal, sol)

    print(f"[SAT_Z3] n={n} solved in {t:.3f}s → {out_path}")
