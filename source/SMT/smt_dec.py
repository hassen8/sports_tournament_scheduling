# source/SMT/smt_dec.py
#
# SMT decision model for the STS problem.
# Same match-based encoding as SAT_Z3, but in Z3's SMT style
# with Bool + cardinalities + no optimisation.
#
# JSON key: "SMT_DEC"

import sys
import time
from itertools import combinations
from pathlib import Path
from z3 import Solver, Bool, AtLeast, AtMost, sat

# import write_result_json
sys.path.append(str(Path(__file__).resolve().parents[1]))
from common.io_json import write_result_json


def build_smt_dec_model(n):
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

    # 1) slot capacity
    for p in range(1, periods + 1):
        for w in range(1, weeks + 1):
            slot = [M_var(i, j, p, w) for (i, j) in pairs]
            exactly_one(slot)

    # 2) unique meeting
    for (i, j) in pairs:
        lits = []
        for p in range(1, periods + 1):
            for w in range(1, weeks + 1):
                lits.append(M_var(i, j, p, w))
        exactly_one(lits)

    # 3) weekly participation
    for t in teams:
        for w in range(1, weeks + 1):
            week_lits = []
            for (i, j) in pairs:
                if t == i or t == j:
                    for p in range(1, periods + 1):
                        week_lits.append(M_var(i, j, p, w))
            exactly_one(week_lits)

    # 4) at most two appearances per period
    for t in teams:
        for p in range(1, periods + 1):
            app = []
            for w in range(1, weeks + 1):
                for (i, j) in pairs:
                    if t == i or t == j:
                        app.append(M_var(i, j, p, w))
            at_most_two(app)

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


def solve_smt_dec(n):
    s, M = build_smt_dec_model(n)
    start = time.time()
    res = s.check()
    elapsed = int(time.time() - start)

    if res != sat:
        return None, 300, M, False

    return s.model(), elapsed, M, True


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python smt_dec.py <n>")

    n = int(sys.argv[1])
    model, t, M, ok = solve_smt_dec(n)

    sol = extract_schedule(model, n, M) if ok else []
    optimal = ok

    out_path = f"res/SMT/{n}.json"
    Path("res/SMT").mkdir(parents=True, exist_ok=True)

    write_result_json("SMT_DEC", n, out_path, t, optimal, sol, obj=None)
    print(f"[SMT_DEC] n={n} time={t}s optimal={optimal}")
