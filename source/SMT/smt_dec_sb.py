# source/SMT/smt_dec_sb.py
#
# SMT decision model with symmetry breaking:
# Fix week 1 to (1,2), (3,4), ..., (2k-1,2k)
#
# JSON key: "SMT_DEC_SB"

import sys
import time
from itertools import combinations
from pathlib import Path
from z3 import Solver, Bool, AtLeast, AtMost, sat

sys.path.append(str(Path(__file__).resolve().parents[1]))
from common.io_json import write_result_json


def build_smt_dec_sb_model(n):
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
        else:
            s.add(AtLeast(*lits, 1))
            s.add(AtMost(*lits, 1))

    def at_most_two(lits):
        if len(lits) > 2:
            s.add(AtMost(*lits, 2))

    teams = list(range(1, n + 1))
    pairs = list(combinations(teams, 2))

    # main constraints (same as smt_dec) 

    # 1) slot
    for p in range(1, periods + 1):
        for w in range(1, weeks + 1):
            slot_lits = [M_var(i, j, p, w) for (i, j) in pairs]
            exactly_one(slot_lits)

    # 2) pair
    for (i, j) in pairs:
        lits = [M_var(i, j, p, w)
                for p in range(1, periods + 1)
                for w in range(1, weeks + 1)]
        exactly_one(lits)

    # 3) weekly
    for t in teams:
        for w in range(1, weeks + 1):
            week_lits = []
            for (i, j) in pairs:
                if t == i or t == j:
                    for p in range(1, periods + 1):
                        week_lits.append(M_var(i, j, p, w))
            exactly_one(week_lits)

    # 4) period ≤2
    for t in teams:
        for p in range(1, periods + 1):
            app = []
            for w in range(1, weeks + 1):
                for (i, j) in pairs:
                    if t == i or t == j:
                        app.append(M_var(i, j, p, w))
            at_most_two(app)

    # symmetry breaking: fix week 1 
    for k in range(1, periods + 1):
        i = 2*k - 1
        j = 2*k
        s.add(M_var(i, j, k, 1))  # period k, week 1

    return s, M


def extract_schedule(model, n, M):
    periods = n // 2
    weeks = n - 1
    sol = [[None for _ in range(weeks)] for _ in range(periods)]
    teams = list(range(1, n + 1))

    for p in range(1, periods + 1):
        for w in range(1, weeks + 1):
            for (i, j) in combinations(teams, 2):
                if model.eval(M[(i, j, p, w)], model_completion=True):
                    sol[p - 1][w - 1] = [i, j]
                    break

    return sol


def solve_smt_dec_sb(n):
    s, M = build_smt_dec_sb_model(n)
    start = time.time()
    res = s.check()
    elapsed = int(time.time() - start)

    if res != sat:
        return None, 300, M, False

    return s.model(), elapsed, M, True


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python smt_dec_sb.py <n>")

    n = int(sys.argv[1])
    model, t, M, ok = solve_smt_dec_sb(n)

    sol = extract_schedule(model, n, M) if ok else []
    optimal = ok

    out_path = f"res/SMT/{n}.json"
    Path("res/SMT").mkdir(parents=True, exist_ok=True)

    write_result_json("SMT_DEC_SB", n, out_path, t, optimal, sol, obj=None)
    print(f"[SMT_DEC_SB] n={n} time={t}s optimal={optimal}")
