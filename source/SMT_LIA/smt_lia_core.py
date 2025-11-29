# source/SMT_LIA/smt_lia_core.py
#
# QF-LIA core model for STS with home/away.
# Variables:
#   H_{i,j,p,w} ∈ {0,1}  -> team i plays at home vs j in period p, week w
#
# Constraints mirror SMT/smt_core.py but in linear arithmetic:
#   - Slot:   exactly 1 match per (period, week)
#   - Pair:   each pair (i,j) plays exactly once (home or away)
#   - Weekly: each team plays exactly once per week
#   - Period: each team plays at most twice in the same period
#   - Optional symmetry breaking (SB1 + SB2)
#   - Optional fairness (home/away balance via max_diff)
#
# Exposes:
#   build_smt_lia_model(n, use_symmetry=False, max_diff=None, timeout_ms=300000)
#   extract_schedule_lia(model, n, H, Weeks, Periods)
#   binary_search_max_diff_lia(n, use_symmetry=False, time_limit_sec=300)

from z3 import *
import time


def build_smt_lia_model(n, use_symmetry=False, max_diff=None, timeout_ms=300000):
    if n % 2 != 0:
        raise ValueError("n must be even")

    periods = n // 2
    weeks = n - 1
    teams = list(range(1, n + 1))
    Weeks = list(range(1, weeks + 1))
    Periods = list(range(1, periods + 1))

    s = Solver()
    s.set("timeout", timeout_ms)

    H = {}

    def H_var(i, j, p, w):
        key = (i, j, p, w)
        if key not in H:
            v = Int(f"H_{i}_{j}_P{p}_W{w}")
            # domain 0/1
            s.add(v >= 0, v <= 1)
            H[key] = v
        return H[key]

    # -------------------
    # 1. Slot constraint
    # -------------------
    # For each period p and week w, exactly one match scheduled.
    for p in Periods:
        for w in Weeks:
            s.add(
                Sum(
                    H_var(i, j, p, w)
                    for i in teams
                    for j in teams
                    if i != j
                ) == 1
            )

    # -------------------
    # 2. Pair constraint
    # -------------------
    # For each unordered pair (i,j), they meet exactly once (home or away).
    for i in teams:
        for j in teams:
            if i < j:
                s.add(
                    Sum(
                        H_var(i, j, p, w) + H_var(j, i, p, w)
                        for p in Periods
                        for w in Weeks
                    ) == 1
                )

    # -------------------
    # 3. Weekly constraint
    # -------------------
    # Each team plays exactly once per week.
    for t in teams:
        for w in Weeks:
            s.add(
                Sum(
                    H_var(t, opp, p, w) + H_var(opp, t, p, w)
                    for p in Periods
                    for opp in teams
                    if opp != t
                ) == 1
            )

    # -------------------
    # 4. Period constraint
    # -------------------
    # Each team appears in a given period at most twice (over all weeks).
    for t in teams:
        for p in Periods:
            s.add(
                Sum(
                    H_var(t, opp, p, w) + H_var(opp, t, p, w)
                    for w in Weeks
                    for opp in teams
                    if opp != t
                ) <= 2
            )

    # -------------------
    # Symmetry breaking
    # -------------------
    if use_symmetry:
        # SB1: fix pairs (2k-1, 2k) in week 1, period k
        for k in Periods:
            i = 2 * k - 1
            j = 2 * k
            if j <= n:
                s.add(
                    H_var(i, j, k, 1) + H_var(j, i, k, 1) >= 1
                )

        # SB2: team 1 plays opponent (w+1) in week w
        for w in Weeks:
            opp = w + 1
            if opp <= n:
                s.add(
                    Sum(
                        H_var(1, opp, p, w) + H_var(opp, 1, p, w)
                        for p in Periods
                    ) >= 1
                )

    # -------------------
    # Fairness constraints (optional)
    # -------------------
    if max_diff is not None:
        total_games = weeks
        for t in teams:
            home_sum = Sum(
                H_var(t, opp, p, w)
                for opp in teams
                if opp != t
                for p in Periods
                for w in Weeks
            )
            min_home = (total_games - max_diff) // 2
            max_home = (total_games + max_diff) // 2
            s.add(home_sum >= min_home, home_sum <= max_home)

    return s, H, Weeks, Periods


def extract_schedule_lia(model, n, H, Weeks, Periods):
    """
    Build schedule matrix (periods x weeks) with [home, away] pairs
    from an Int(0/1) model.
    """
    periods = len(Periods)
    weeks = len(Weeks)
    teams = list(range(1, n + 1))

    sol = [[None for _ in range(weeks)] for _ in range(periods)]

    for pi, p in enumerate(Periods):
        for wi, w in enumerate(Weeks):
            for i in teams:
                for j in teams:
                    if i == j:
                        continue
                    v = model.eval(H[(i, j, p, w)], model_completion=True)
                    try:
                        if v.as_long() == 1:
                            sol[pi][wi] = [i, j]
                            break
                    except Exception:
                        # If model gives non-int (shouldn't happen), ignore
                        pass
                if sol[pi][wi] is not None:
                    break

    return sol


def binary_search_max_diff_lia(n, use_symmetry=False, time_limit_sec=300):
    """
    Binary search on max_diff for fairness.
    Returns:
        (best_model, best_diff, best_H, best_Weeks, best_Periods, proved_optimal, total_time)
    """
    low, high = 0, n - 1
    best = None
    best_model = None
    best_H = None
    best_W = None
    best_P = None

    start = time.time()
    saw_unknown = False

    while low <= high:
        elapsed = time.time() - start
        remaining = time_limit_sec - elapsed
        if remaining <= 0:
            saw_unknown = True
            break

        mid = (low + high) // 2
        timeout_ms = max(1, int(remaining * 1000))

        s, H, Weeks, Periods = build_smt_lia_model(
            n, use_symmetry=use_symmetry, max_diff=mid, timeout_ms=timeout_ms
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
            # unknown / timeout
            saw_unknown = True
            break

    total_time = time.time() - start
    proved_optimal = (best is not None) and (low > high) and (not saw_unknown)

    return best_model, best, best_H, best_W, best_P, proved_optimal, total_time
# source/SMT_LIA/smt_lia_core.py
#
# QF-LIA SMT core for the STS problem.
# Uses Bool variables H_{i,j,p,w} and linear arithmetic constraints
# (Sum(If(...))) so that the exported SMT-LIB is in QF_LIA.
#
# Exposes:
#   build_smt_lia_model(n, use_symmetry=False, max_diff=None, timeout_ms=300000)
#   extract_lia_schedule(model, H, Weeks, Periods, n)
#   binary_search_max_diff_lia(n, use_symmetry=False, timeout_sec=300)

from z3 import *
import time


def _sum_bool(lits):
    """Sum of Bool literals as Int: Sum(If(l,1,0))."""
    if not lits:
        return IntVal(0)
    return Sum([If(l, 1, 0) for l in lits])


def exactly_one(lits):
    """Exactly one of the Bool literals is true."""
    return _sum_bool(lits) == 1


def at_most_k(lits, k):
    """At most k of the Bool literals are true."""
    return _sum_bool(lits) <= k


def at_least_k(lits, k):
    """At least k of the Bool literals are true."""
    return _sum_bool(lits) >= k


def build_smt_lia_model(n, use_symmetry=False, max_diff=None, timeout_ms=300000):
    """
    Build the QF-LIA SMT model for the STS with n teams.

    n must be even.

    Args:
        n            : number of teams
        use_symmetry : add SB1 + SB2 symmetry breaking
        max_diff     : if not None, enforce fairness:
                       for each team t, #home ∈ [ (W-max_diff)/2 , (W+max_diff)/2 ]
        timeout_ms   : Z3 timeout in milliseconds

    Returns:
        s       : Z3 Solver
        H       : dict[(i,j,p,w)] -> BoolRef
        Weeks   : list of week indices (1..n-1)
        Periods : list of period indices (1..n/2)
    """
    if n % 2 != 0:
        raise ValueError("n must be even")

    periods = n // 2
    weeks = n - 1
    teams = list(range(1, n + 1))
    Weeks = list(range(1, weeks + 1))
    Periods = list(range(1, periods + 1))

    s = Solver()
    s.set("timeout", timeout_ms)

    # H_{i,j,p,w} : team i plays at home vs j in period p, week w
    H = {}

    def H_var(i, j, p, w):
        key = (i, j, p, w)
        if key not in H:
            H[key] = Bool(f"H_{i}_{j}_P{p}_W{w}")
        return H[key]

    # 1) Slot constraint: each (p,w) has exactly one ordered pair (i,j)
    for p in Periods:
        for w in Weeks:
            lits = [H_var(i, j, p, w) for i in teams for j in teams if i != j]
            s.add(exactly_one(lits))

    # 2) Pair constraint: each unordered pair {i,j} meets exactly once (home or away)
    for i in teams:
        for j in teams:
            if i < j:
                lits = []
                for p in Periods:
                    for w in Weeks:
                        lits.append(H_var(i, j, p, w))
                        lits.append(H_var(j, i, p, w))
                s.add(exactly_one(lits))

    # 3) Weekly constraint: each team plays exactly one match per week
    for t in teams:
        for w in Weeks:
            lits = []
            for p in Periods:
                for opp in teams:
                    if opp == t:
                        continue
                    lits.append(H_var(t, opp, p, w))
                    lits.append(H_var(opp, t, p, w))
            s.add(exactly_one(lits))

    # 4) Period constraint: each team appears in a given period at most twice overall
    for t in teams:
        for p in Periods:
            lits = []
            for w in Weeks:
                for opp in teams:
                    if opp == t:
                        continue
                    lits.append(H_var(t, opp, p, w))
                    lits.append(H_var(opp, t, p, w))
            s.add(at_most_k(lits, 2))

    # 5) Symmetry breaking (if enabled)
    if use_symmetry:
        # SB1: in week 1, period k: teams (2k-1, 2k) play (either home/away)
        for k in Periods:
            i = 2 * k - 1
            j = 2 * k
            if j <= n:
                s.add(Or(H_var(i, j, k, 1), H_var(j, i, k, 1)))

        # SB2: team 1's opponent in week w is w+1
        for w in Weeks:
            opp = w + 1
            if opp <= n:
                lits = []
                for p in Periods:
                    lits.append(H_var(1, opp, p, w))
                    lits.append(H_var(opp, 1, p, w))
                s.add(Or(*lits))

    # 6) Fairness constraints (if max_diff not None):
    #    For each team t, number of home games is in a small interval.
    if max_diff is not None:
        total_games = weeks  # each team plays once per week
        min_home = (total_games - max_diff) // 2
        max_home_val = (total_games + max_diff) // 2

        for t in teams:
            home_lits = []
            for j in teams:
                if j == t:
                    continue
                for p in Periods:
                    for w in Weeks:
                        home_lits.append(H_var(t, j, p, w))

            s.add(at_least_k(home_lits, min_home))
            s.add(at_most_k(home_lits, max_home_val))

    return s, H, Weeks, Periods


def extract_lia_schedule(model, H, Weeks, Periods, n):
    """
    Extract schedule matrix from model:
    sol[period_index][week_index] = [home, away]
    """
    sol = [[None for _ in Weeks] for _ in Periods]
    teams = list(range(1, n + 1))

    for pi, p in enumerate(Periods):
        for wi, w in enumerate(Weeks):
            for i in teams:
                for j in teams:
                    if i == j:
                        continue
                    key = (i, j, p, w)
                    v = H[key]
                    if is_true(model.eval(v, model_completion=True)):
                        sol[pi][wi] = [i, j]
                        break
                if sol[pi][wi] is not None:
                    break
    return sol


def binary_search_max_diff_lia(n, use_symmetry=False, timeout_sec=300):
    """
    Binary search on max_diff to minimize home/away imbalance.

    Returns:
        best_model, best_diff, best_H, best_W, best_P, proved_optimal, elapsed
    """
    low, high = 0, n - 1
    best_model = None
    best_diff = None
    best_H = best_W = best_P = None

    start = time.time()
    proved_optimal = False

    while low <= high:
        # Global timeout approx: stop if close to timeout_sec
        now = time.time()
        if now - start > timeout_sec:
            break

        mid = (low + high) // 2
        s, H, Weeks, Periods = build_smt_lia_model(
            n,
            use_symmetry=use_symmetry,
            max_diff=mid,
            timeout_ms=int((timeout_sec - (now - start)) * 1000)
        )

        res = s.check()
        if res == sat:
            best_model = s.model()
            best_diff = mid
            best_H = H
            best_W = Weeks
            best_P = Periods
            high = mid - 1
        else:
            low = mid + 1

    elapsed = time.time() - start
    if best_model is not None and low > high:
        proved_optimal = True

    return best_model, best_diff, best_H, best_W, best_P, proved_optimal, elapsed
