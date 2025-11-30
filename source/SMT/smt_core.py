# source/SMT/smt_core.py

from z3 import (
    Solver, Bool, And, Or, Not,
    AtLeast, AtMost,
    PbLe, PbGe,
    is_true,
    sat, unsat
)
import time


def exactly_one(lits):
    if not lits:
        return []
    if len(lits) == 1:
        return [lits[0]]
    return [AtLeast(*lits, 1), AtMost(*lits, 1)]


def at_most_k(lits, k):
    if not lits:
        return []
    return [PbLe([(v, 1) for v in lits], k)]


def at_least_k(lits, k):
    if not lits:
        return [PbGe([], k)]
    return [PbGe([(v, 1) for v in lits], k)]


def build_smt_model(n, use_symmetry=False, max_diff=None):
    if n % 2 != 0:
        raise ValueError("n must be even")

    periods = n // 2
    weeks = n - 1

    Teams = range(1, n + 1)
    Periods = range(periods)
    Weeks = range(weeks)

    s = Solver()
    s.set("timeout", 300000)

    M = {}
    H = {}

    def M_var(i, j, p, w):
        if i > j:
            i, j = j, i
        key = (i, j, p, w)
        if key not in M:
            M[key] = Bool(f"M_{i}_{j}_P{p}_W{w}")
        return M[key]

    def H_var(i, j, p, w):
        if i > j:
            i, j = j, i
        key = (i, j, p, w)
        if key not in H:
            H[key] = Bool(f"H_{i}_{j}_P{p}_W{w}")
        return H[key]

    # 1. Slot constraint
    for p in Periods:
        for w in Weeks:
            lits = [M_var(i, j, p, w)
                    for i in Teams for j in Teams if i < j]
            for c in exactly_one(lits):
                s.add(c)

    # 2. Pair plays exactly once
    for i in Teams:
        for j in Teams:
            if i < j:
                lits = [M_var(i, j, p, w)
                        for p in Periods for w in Weeks]
                for c in exactly_one(lits):
                    s.add(c)

    # 3. Weekly constraint
    for t in Teams:
        for w in Weeks:
            lits = []
            for p in Periods:
                for opp in Teams:
                    if opp != t:
                        i, j = (t, opp) if t < opp else (opp, t)
                        lits.append(M_var(i, j, p, w))
            for c in exactly_one(lits):
                s.add(c)

    # 4. Period appearance ≤ 2
    for t in Teams:
        for p in Periods:
            lits = []
            for w in Weeks:
                for opp in Teams:
                    if opp != t:
                        i, j = (t, opp) if t < opp else (opp, t)
                        lits.append(M_var(i, j, p, w))
            for c in at_most_k(lits, 2):
                s.add(c)

    # Symmetry breaking
    if use_symmetry:
        for p in Periods:
            i = 2 * p + 1
            j = 2 * p + 2
            if j <= n:
                s.add(M_var(i, j, p, 0))

        for w in Weeks:
            opp = w + 2
            if opp <= n:
                lits = []
                for p in Periods:
                    i, j = (1, opp) if 1 < opp else (opp, 1)
                    lits.append(M_var(i, j, p, w))
                s.add(Or(*lits))

    # Fairness constraint
    if max_diff is not None:
        total_games = weeks
        min_home = (total_games - max_diff) // 2
        max_home = (total_games + max_diff) // 2

        for t in Teams:
            home_lits = []
            for opp in Teams:
                if opp != t:
                    i, j = (t, opp) if t < opp else (opp, t)
                    for p in Periods:
                        for w in Weeks:
                            m = M_var(i, j, p, w)
                            h = H_var(i, j, p, w)
                            if i == t:
                                home_lits.append(And(m, h))
                            else:
                                home_lits.append(And(m, Not(h)))

            for c in at_least_k(home_lits, min_home):
                s.add(c)
            for c in at_most_k(home_lits, max_home):
                s.add(c)

    return s, M, H, list(Weeks), list(Periods)


def extract_schedule(model, n, M, H, Weeks, Periods):
    sol = [[None for _ in Weeks] for _ in Periods]
    Teams = range(1, n + 1)

    for pi, p in enumerate(Periods):
        for wi, w in enumerate(Weeks):
            for i in Teams:
                for j in Teams:
                    if i < j:
                        key = (i, j, p, w)
                        if key in M and is_true(model.eval(M[key], model_completion=True)):
                            if key in H:
                                home = is_true(model.eval(H[key], model_completion=True))
                                sol[pi][wi] = [i, j] if home else [j, i]
                            else:
                                sol[pi][wi] = [i, j]
                            break
                if sol[pi][wi] is not None:
                    break
    return sol


def binary_search_max_diff(n, use_symmetry=False, time_limit=300):
    start = time.time()
    low, high = 0, n - 1

    best = None
    best_model = None
    best_M = best_H = best_W = best_P = None
    proved_optimal = True

    try:
        while low <= high:
            if time.time() - start > time_limit:
                proved_optimal = False
                break

            mid = (low + high) // 2
            s, M, H, Weeks, Periods = build_smt_model(
                n,
                use_symmetry=use_symmetry,
                max_diff=mid
            )

            try:
                res = s.check()
            except KeyboardInterrupt:
                proved_optimal = False
                break

            if res == sat:
                best = mid
                best_model = s.model()
                best_M, best_H, best_W, best_P = M, H, Weeks, Periods
                high = mid - 1
            elif res == unsat:
                low = mid + 1
            else:
                proved_optimal = False
                break

    except KeyboardInterrupt:
        proved_optimal = False

    elapsed = time.time() - start
    return best_model, best, best_M, best_H, best_W, best_P, proved_optimal, elapsed
