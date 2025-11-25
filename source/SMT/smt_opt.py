# source/SMT/smt_opt.py
#
# SMT optimization model:
#   Minimize F = max_t |home_t - away_t|
#
# JSON key: "SMT_OPT"

import sys
import time
from itertools import combinations
from pathlib import Path
from z3 import Optimize, Bool, Int, If, AtLeast, AtMost, sat

sys.path.append(str(Path(__file__).resolve().parents[1]))
from common.io_json import write_result_json


def build_smt_opt_model(n):
    periods = n // 2
    weeks = n - 1

    opt = Optimize()
    opt.set("timeout", 300000)

    M = {}

    def M_var(i, j, p, w):
        key = (i, j, p, w)
        if key not in M:
            M[key] = Bool(f"M_{i}_{j}_{p}_{w}")
        return M[key]

    def exactly_one(lits):
        if len(lits) == 1:
            opt.add(lits[0])
        else:
            opt.add(AtLeast(*lits, 1))
            opt.add(AtMost(*lits, 1))

    def at_most_two(lits):
        if len(lits) > 2:
            opt.add(AtMost(*lits, 2))

    teams = list(range(1, n + 1))
    pairs = list(combinations(teams, 2))

    #  Feaibility constraints

    # 1) slot assignment
    for p in range(1, periods + 1):
        for w in range(1, weeks + 1):
            slot_lits = [M_var(i, j, p, w) for (i, j) in pairs]
            exactly_one(slot_lits)

    # 2. unique meeting
    for (i, j) in pairs:
        lits = [M_var(i, j, p, w)
                for p in range(1, periods + 1)
                for w in range(1, weeks + 1)]
        exactly_one(lits)

    # 3. weekly exactly one
    for t in teams:
        for w in range(1, weeks + 1):
            week_lits = []
            for (i, j) in pairs:
                if t == i or t == j:
                    for p in range(1, periods + 1):
                        week_lits.append(M_var(i, j, p, w))
            exactly_one(week_lits)

    # 4. period at most two
    for t in teams:
        for p in range(1, periods + 1):
            app = []
            for w in range(1, weeks + 1):
                for (i, j) in pairs:
                    if t == i or t == j:
                        app.append(M_var(i, j, p, w))
            at_most_two(app)

    #Fairness variables 

    home = {}
    away = {}
    diff = {}

    for t in teams:
        home_t = Int(f"home_{t}")
        away_t = Int(f"away_{t}")
        diff_t = Int(f"diff_{t}")

        home_sum = []
        away_sum = []

        for (i, j) in pairs:
            for p in range(1, periods + 1):
                for w in range(1, weeks + 1):
                    v = M_var(i, j, p, w)
                    if t == i:
                        home_sum.append(If(v, 1, 0))
                    if t == j:
                        away_sum.append(If(v, 1, 0))

        opt.add(home_t == sum(home_sum))
        opt.add(away_t == sum(away_sum))
        opt.add(diff_t >= home_t - away_t)
        opt.add(diff_t >= away_t - home_t)
        opt.add(diff_t >= 0)

        home[t] = home_t
        away[t] = away_t
        diff[t] = diff_t

    F = Int("F")
    for t in teams:
        opt.add(F >= diff[t])

    opt.add(F >= 0)
    opt.add(F <= n - 1)

    opt.minimize(F)

    return opt, M, F


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


def solve_smt_opt(n):
    opt, M, F = build_smt_opt_model(n)
    start = time.time()
    res = opt.check()
    elapsed = int(time.time() - start)

    if res != sat:
        return None, 300, M, None, False

    model = opt.model()
    obj = model.eval(F).as_long()
    return model, elapsed, M, obj, True


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python smt_opt.py <n>")

    n = int(sys.argv[1])
    model, t, M, obj, ok = solve_smt_opt(n)

    sol = extract_schedule(model, n, M) if ok else []
    optimal = ok
    obj_val = obj if ok else None

    out_path = f"res/SMT/{n}.json"
    Path("res/SMT").mkdir(parents=True, exist_ok=True)

    write_result_json("SMT_OPT", n, out_path, t, optimal, sol, obj=obj_val)
    print(f"[SMT_OPT] n={n} time={t}s obj={obj_val}")
