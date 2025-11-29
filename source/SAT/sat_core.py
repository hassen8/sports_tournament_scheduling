# source/SAT/sat_core.py
#
# Unified SAT model builder for:
#   - decision (no SB)
#   - decision + SB
#   - optimization (no SB)
#   - optimization + SB
#
# Exposes:
#   build_model(n, use_symmetry, max_diff)
#   solve_model(...)
#   extract_schedule(...)
#   binary_search_max_diff(...)
#
# All SAT scripts import from here.

import time
from z3 import Solver, Bool, Or, AtLeast, AtMost, PbLe, PbGe, sat


# ---------------------------
# Helpers
# ---------------------------

def exactly_one(lits):
    if len(lits) == 0:
        return []
    if len(lits) == 1:
        return [lits[0]]
    return [AtLeast(*lits, 1), AtMost(*lits, 1)]


def at_most_k(lits, k):
    if len(lits) == 0:
        return []
    return [PbLe([(v, 1) for v in lits], k)]


def at_least_k(lits, k):
    if len(lits) == 0:
        return [PbGe([], k)]
    return [PbGe([(v, 1) for v in lits], k)]


# Build full SAT model (decision or optimization)

def build_model(n, use_symmetry=False, max_diff=None):
    """
    Build SAT model with flags:
        use_symmetry = apply symmetry breaking
        max_diff     = fairness bound (None → decision)
    """
    if n % 2 != 0:
        raise ValueError("n must be even")

    periods = n // 2
    weeks = n - 1
    teams = list(range(1, n + 1))
    Weeks = list(range(1, weeks + 1))
    Periods = list(range(1, periods + 1))

    s = Solver()
    s.set("timeout", 300000)   # 300 seconds

    # Directed match variable: i home vs j away in (p,w)
    H = {}
    def H_var(i, j, p, w):
        key = (i, j, p, w)
        if key not in H:
            H[key] = Bool(f"H_{i}_{j}_P{p}_W{w}")
        return H[key]


    # - Base constraints

    # 1) Slot: each (period, week) has exactly one match
    for p in Periods:
        for w in Weeks:
            lits = [H_var(i, j, p, w) for i in teams for j in teams if i != j]
            for c in exactly_one(lits):
                s.add(c)

    # 2) Pair: each unordered pair plays exactly once
    for i in teams:
        for j in teams:
            if i < j:
                lits = []
                for p in Periods:
                    for w in Weeks:
                        lits.append(H_var(i, j, p, w))
                        lits.append(H_var(j, i, p, w))
                for c in exactly_one(lits):
                    s.add(c)

    # 3) Weekly: each team plays exactly once per week
    for t in teams:
        for w in Weeks:
            week_lits = []
            for p in Periods:
                for opp in teams:
                    if opp == t:
                        continue
                    week_lits.append(H_var(t, opp, p, w))
                    week_lits.append(H_var(opp, t, p, w))
            for c in exactly_one(week_lits):
                s.add(c)

    # 4) Period: each team appears at most twice in same period
    for t in teams:
        for p in Periods:
            lits = []
            for w in Weeks:
                for opp in teams:
                    if opp != t:
                        lits.append(H_var(t, opp, p, w))
                        lits.append(H_var(opp, t, p, w))
            for c in at_most_k(lits, 2):
                s.add(c)


    #  Symmetry Breaking 

    if use_symmetry:
        # SB1: fix week 1 canonical pairings
        for k in Periods:
            i = 2*k - 1
            j = 2*k
            if j <= n:
                s.add(Or(H_var(i,j,k,1), H_var(j,i,k,1)))

        # SB2: team 1 opponent sequence (week w = team w+1)
        for w in Weeks:
            opp = w + 1
            if opp <= n:
                lits = []
                for p in Periods:
                    lits.append(H_var(1, opp, p, w))
                    lits.append(H_var(opp, 1, p, w))
                s.add(Or(*lits))


    # Fairness (optional)

    if max_diff is not None:
        total_games = weeks

        for t in teams:
            home_lits = []
            for j in teams:
                if j == t:
                    continue
                for p in Periods:
                    for w in Weeks:
                        home_lits.append(H_var(t,j,p,w))   # t home only

            min_home = (total_games - max_diff) // 2
            max_home = (total_games + max_diff) // 2

            for c in at_least_k(home_lits, min_home):
                s.add(c)
            for c in at_most_k(home_lits, max_home):
                s.add(c)


    return s, H, Weeks, Periods


# Extraction

def extract_schedule(model, n, H, Weeks, Periods):
    sol = [[None for _ in Weeks] for _ in Periods]
    teams = list(range(1, n+1))

    for pi,p in enumerate(Periods):
        for wi,w in enumerate(Weeks):
            for i in teams:
                for j in teams:
                    if i != j and model.eval(H[(i,j,p,w)], model_completion=True):
                        sol[pi][wi] = [i,j]
                        break
    return sol


# Optimization loop (binary search)

def binary_search_max_diff(n, use_symmetry=False):
    low, high = 0, n-1
    best = None
    best_model = None
    best_H = None
    best_W = None
    best_P = None

    while low <= high:
        mid = (low + high) // 2
        s, H, W, P = build_model(n, use_symmetry=use_symmetry, max_diff=mid)
        if s.check() == sat:
            best = mid
            best_model = s.model()
            best_H = H
            best_W = W
            best_P = P
            high = mid - 1
        else:
            low = mid + 1

    return best_model, best, best_H, best_W, best_P
