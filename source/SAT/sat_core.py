import time
from z3 import Solver, Bool, Or, Not, And, AtMost, AtLeast, sat

def ordered_pair(i, j):
    return (i, j) if i < j else (j, i)

def exactly_one(s, lits):
    if not lits:
        return
    if len(lits) == 1:
        s.add(lits[0])
    else:
        s.add(AtLeast(*lits, 1))
        s.add(AtMost(*lits, 1))

def build_model(n, use_symmetry=False, max_diff=None):
    if n % 2 != 0:
        raise ValueError("n must be even")

    periods = n // 2
    weeks = n - 1

    teams = list(range(1, n + 1))
    Weeks = list(range(weeks))
    Periods = list(range(periods))

    s = Solver()
    s.set("timeout", 300000)

    M = {}
    H = {}

    def M_var(i, j, p, w):
        i, j = ordered_pair(i, j)
        key = (i, j, p, w)
        if key not in M:
            M[key] = Bool(f"M_{i}_{j}_P{p}_W{w}")
        return M[key]

    def H_var(i, j, p, w):
        i, j = ordered_pair(i, j)
        key = (i, j, p, w)
        if key not in H:
            H[key] = Bool(f"H_{i}_{j}_P{p}_W{w}")
        return H[key]

    for i in teams:
        for j in teams:
            if i < j:
                lits = [M_var(i, j, p, w) for p in Periods for w in Weeks]
                exactly_one(s, lits)

    for t in teams:
        for w in Weeks:
            lits = []
            for p in Periods:
                for opp in teams:
                    if opp == t:
                        continue
                    i, j = ordered_pair(t, opp)
                    lits.append(M_var(i, j, p, w))
            exactly_one(s, lits)

    for p in Periods:
        for w in Weeks:
            lits = []
            for i in teams:
                for j in teams:
                    if i < j:
                        lits.append(M_var(i, j, p, w))
            exactly_one(s, lits)

    for t in teams:
        for p in Periods:
            lits = []
            for opp in teams:
                if opp == t:
                    continue
                for w in Weeks:
                    i, j = ordered_pair(t, opp)
                    lits.append(M_var(i, j, p, w))
            if len(lits) > 2:
                s.add(AtMost(*lits, 2))

    if use_symmetry:
        for p in Periods:
            i = 2 * p + 1
            j = 2 * p + 2
            if j <= n:
                s.add(M_var(i, j, p, 0))
                s.add(H_var(i, j, p, 0))

        for w in Weeks:
            opp = w + 2
            if opp <= n:
                s.add(Or(*[M_var(1, opp, p, w) for p in Periods]))

        for opp in teams:
            if opp == 1:
                continue
            for p in Periods:
                for w in Weeks:
                    m = M_var(1, opp, p, w)
                    h = H_var(1, opp, p, w)
                    s.add(Or(Not(m), h))

    if max_diff is None:
        return s, M, H, Weeks, Periods

    total_games = weeks
    min_home = (total_games - max_diff) // 2
    max_home = (total_games + max_diff) // 2

    for t in teams:
        home_lits = []
        for opp in teams:
            if opp == t:
                continue
            for p in Periods:
                for w in Weeks:
                    i, j = ordered_pair(t, opp)
                    m = M_var(i, j, p, w)
                    h = H_var(i, j, p, w)

                    t_home = Bool(f"HOME_{t}_{opp}_{p}_{w}")
                    home_lits.append(t_home)

                    if t == i:
                        s.add(Or(Not(t_home), m))
                        s.add(Or(Not(t_home), h))
                        s.add(Or(Not(m), Not(h), t_home))
                    else:
                        s.add(Or(Not(t_home), m))
                        s.add(Or(Not(t_home), Not(h)))
                        s.add(Or(Not(m), h, t_home))

        if min_home > 0:
            s.add(AtLeast(*home_lits, min_home))
        s.add(AtMost(*home_lits, max_home))

    return s, M, H, Weeks, Periods

def extract_schedule(model, n, M, H, Weeks, Periods):
    sol = [[None for _ in Weeks] for _ in Periods]
    teams = list(range(1, n + 1))

    for pi, p in enumerate(Periods):
        for wi, w in enumerate(Weeks):
            for i in teams:
                for j in teams:
                    if i < j:
                        key = (i, j, p, w)
                        if key in M and model.eval(M[key], model_completion=True):
                            if key in H:
                                home_first = model.eval(H[key], model_completion=True)
                                sol[pi][wi] = [i, j] if home_first else [j, i]
                            else:
                                sol[pi][wi] = [i, j]
                            break
                if sol[pi][wi] is not None:
                    break

    return sol

from z3 import Bool

def binary_search_max_diff(n, use_symmetry=False, verbose=False):
    base_s, M, H, W, P = build_model(n, use_symmetry=use_symmetry, max_diff=None)

    low, high = 0, n - 1
    best = None
    best_model = None
    best_M = best_H = best_W = best_P = None

    while low <= high:
        mid = (low + high) // 2

        s = Solver()
        s.set("timeout", 300000)
        for a in base_s.assertions():
            s.add(a)

        total_games = n - 1
        min_home = (total_games - mid) // 2
        max_home = (total_games + mid) // 2

        for t in range(1, n + 1):
            t_home_lits = []

            for (i, j, p, w), m in M.items():

                h = H.get((i, j, p, w))
                if h is None:
                    h = Bool(f"H_{i}_{j}_P{p}_W{w}")
                    H[(i, j, p, w)] = h

                if t == i:
                    htmp = Bool(f"HMT_{t}_{i}_{j}_{p}_{w}")
                    s.add(htmp == And(m, h))
                    t_home_lits.append(htmp)

                elif t == j:
                    htmp = Bool(f"HMT_{t}_{i}_{j}_{p}_{w}")
                    s.add(htmp == And(m, Not(h)))
                    t_home_lits.append(htmp)

            if min_home > 0:
                s.add(AtLeast(*t_home_lits, min_home))
            s.add(AtMost(*t_home_lits, max_home))

        res = s.check()

        if res == sat:
            best = mid
            best_model = s.model()
            best_M, best_H, best_W, best_P = M, H, W, P
            high = mid - 1
        else:
            low = mid + 1

    if best is None:
        return None, None, None, None, None, None

    return best_model, best, best_M, best_H, best_W, best_P
