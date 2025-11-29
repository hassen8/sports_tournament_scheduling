# source/SMT/smt_core.py
#
# Core SMT model builder for:
#   - decision (no symmetry)
#   - decision + symmetry
#   - optimization (no symmetry)
#   - optimization + symmetry
#
# Exposes:
#   build_smt_model(n, use_symmetry=False, max_diff=None)
#   extract_schedule(model, n, H, Weeks, Periods)
#   binary_search_max_diff(n, use_symmetry=False, time_limit=300)
#
# The structure mirrors sat_core.py but uses the SMT-oriented Z3 API.

from z3 import *
import time


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
        # If we require at least k>0 from an empty list, it's unsatisfiable,
        # but PbGe([], k) is the canonical encoding.
        return [PbGe([], k)]
    return [PbGe([(v, 1) for v in lits], k)]


def build_smt_model(n, use_symmetry=False, max_diff=None):
    if n % 2 != 0:
        raise ValueError("n must be even")

    periods = n // 2
    weeks = n - 1
    teams = list(range(1, n + 1))
    Weeks = list(range(1, weeks + 1))
    Periods = list(range(1, periods + 1))

    s = Solver()
    # Per-call timeout (ms) – global 300s limit is enforced in the wrappers
    s.set("timeout", 300000)

    H = {}

    def H_var(i, j, p, w):
        key = (i, j, p, w)
        if key not in H:
            H[key] = Bool(f"H_{i}_{j}_P{p}_W{w}")
        return H[key]

    # Slot constraint: exactly one match per (period, week) slot
    for p in Periods:
        for w in Weeks:
            lits = [H_var(i, j, p, w) for i in teams for j in teams if i != j]
            for c in exactly_one(lits):
                s.add(c)

    # Pair constraint: each pair (i,j) plays exactly once (home or away)
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

    # Weekly constraint: each team plays exactly one match per week
    for t in teams:
        for w in Weeks:
            lits = []
            for p in Periods:
                for opp in teams:
                    if opp != t:
                        lits.append(H_var(t, opp, p, w))
                        lits.append(H_var(opp, t, p, w))
            for c in exactly_one(lits):
                s.add(c)

    # Period constraint: each team appears in at most 2 matches in a given period over the whole tournament
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

    # Symmetry breaking
    if use_symmetry:
        # SB1: Fix structure of first week by pairing (1,2), (3,4), ...
        for k in Periods:
            i = 2 * k - 1
            j = 2 * k
            if j <= n:
                s.add(Or(H_var(i, j, k, 1), H_var(j, i, k, 1)))

        # SB2: Fix opponents for team 1 across weeks
        for w in Weeks:
            opp = w + 1
            if opp <= n:
                lits = []
                for p in Periods:
                    lits.append(H_var(1, opp, p, w))
                    lits.append(H_var(opp, 1, p, w))
                s.add(Or(*lits))

    # Fairness optimization: constrain home-game counts within [min_home, max_home]
    if max_diff is not None:
        total_games = weeks

        for t in teams:
            home_lits = []
            for j in teams:
                if j == t:
                    continue
                for p in Periods:
                    for w in Weeks:
                        home_lits.append(H_var(t, j, p, w))

            min_home = (total_games - max_diff) // 2
            max_home = (total_games + max_diff) // 2

            for c in at_least_k(home_lits, min_home):
                s.add(c)
            for c in at_most_k(home_lits, max_home):
                s.add(c)

    return s, H, Weeks, Periods


def extract_schedule(model, n, H, Weeks, Periods):
    sol = [[None for _ in Weeks] for _ in Periods]
    teams = list(range(1, n + 1))

    for pi, p in enumerate(Periods):
        for wi, w in enumerate(Weeks):
            for i in teams:
                for j in teams:
                    if i != j:
                        if model.eval(H[(i, j, p, w)], model_completion=True):
                            sol[pi][wi] = [i, j]
                            break
    return sol


def binary_search_max_diff(n, use_symmetry=False, time_limit=300):
    """
    Binary search on max_diff with a GLOBAL time limit.

    Returns:
        best_model      -> Z3 model or None
        best_diff       -> int or None
        best_H, best_W, best_P
        proved_optimal  -> True iff search completed without hitting time/unknown
        elapsed         -> total wall-clock time (float seconds)
    """
    start = time.time()
    low, high = 0, n - 1
    best = None
    best_model = None
    best_H = None
    best_W = None
    best_P = None
    proved_optimal = True

    while low <= high:
        now = time.time()
        if now - start > time_limit:
            proved_optimal = False
            break

        mid = (low + high) // 2
        s, H, Weeks, Periods = build_smt_model(
            n,
            use_symmetry=use_symmetry,
            max_diff=mid
        )

        res = s.check()
        if res == sat:
            best = mid
            best_model = s.model()
            best_H = H
            best_W = Weeks
            best_P = Periods
            high = mid - 1
        elif res == unsat:
            low = mid + 1
        else:
            # s.check() returned unknown or hit per-call timeout
            proved_optimal = False
            break

    elapsed = time.time() - start
    return best_model, best, best_H, best_W, best_P, proved_optimal, elapsed
