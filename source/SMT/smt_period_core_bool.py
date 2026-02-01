#!/usr/bin/env python3
from z3 import Solver, Bool, Not, SolverFor, PbEq, PbLe, PbGe, Implies, And, Optimize, Int, If, Sum
from round_robin import circle_method_pairs


def pb_exactly_one(s: Solver, lits):
    """
    sum(lits) == 1 
    """
    s.add(PbEq([(x, 1) for x in lits], 1))


def pb_at_most_k(s: Solver, lits, k: int):
    """
    sum(lits) <= k 
    """
    s.add(PbLe([(x, 1) for x in lits], k))


def pb_at_least_k(s: Solver, lits, k: int):
    """
    sum(lits) >= k 
    """
    s.add(PbGe([(x, 1) for x in lits], k))


def pb_between_1_and_2(s: Solver, lits):
    """
    Enforce 1 <= sum(lits) <= 2
    """
    pb_at_least_k(s, lits, 1)
    pb_at_most_k(s, lits, 2)


def build_model(
    n: int,
    use_sym: bool = False,
    anchor_week: int = 0,
    with_home: bool = False,
    max_diff: int | None = None,
    timeout_ms: int = 300_000,
    pin_team1_weeks: int = 0,
    optimize: bool = False
):

    if n % 2 != 0:
        raise ValueError("n must be even")

    P = n // 2
    W = n - 1
    M = n // 2
    weeks = circle_method_pairs(n)

    seen = set()
    for w in range(W):
        used = set()
        for (a, b) in weeks[w]:
            if a == b:
                raise RuntimeError(f"Bad pairing: self match ({a},{b}) week {w}")
            if a in used or b in used:
                raise RuntimeError(f"Bad week {w}: team repeats in week")
            used.add(a)
            used.add(b)
            key = (a, b) if a < b else (b, a)
            if key in seen:
                raise RuntimeError(f"Bad RR: duplicate pair {key} appears again")
            seen.add(key)

    if len(seen) != n * (n - 1) // 2:
        raise RuntimeError("Bad RR: not all pairs generated")
    
    if optimize:
        s = Optimize()
        solver_tag = "Z3_OPT"
    else:
        solver_tag = "SAT"
        try:
            s = SolverFor("SAT")
        except Exception:
            s = Solver()
            solver_tag = "SMT"

    s.set("timeout", timeout_ms)

    try:
        s.set("random_seed", 0)
    except Exception:
        pass

    X = [[[Bool(f"X_{w}_{m}_{p}") for p in range(P)] for m in range(M)] for w in range(W)]

    home = None
    if with_home:
        home = [[Bool(f"home_{w}_{m}") for m in range(M)] for w in range(W)]

    # 1 each match assigned to exactly one period
    for w in range(W):
        for m in range(M):
            pb_exactly_one(s, X[w][m])

    # 2 each period has exactly one match per week
    for w in range(W):
        for p in range(P):
            pb_exactly_one(s, [X[w][m][p] for m in range(M)])

    # Precompute match_of[w][t]
    match_of = [[None] * (n + 1) for _ in range(W)]
    for w in range(W):
        for m, (a, b) in enumerate(weeks[w]):
            match_of[w][a] = m
            match_of[w][b] = m

    # 3 team appears in same period at most twice
        #  For each team t and period p:
    #    occurrences are forced to be either 1 or 2 (never 0),
    #    and each team has exactly one period where it occurs exactly 1 time.
    one = [[Bool(f"one_{t}_{p}") for p in range(P)] for t in range(1, n + 1)]

    for t in range(1, n + 1):
        for p in range(P):
            lits = [X[w][match_of[w][t]][p] for w in range(W)]

            # 1 <= occ(t,p) <= 2   Implied constraint
            pb_between_1_and_2(s, lits)

            # Define one[t][p] <-> (occ(t,p) == 1)
            # If one[t][p] then occ <= 1 (and we already have occ >= 1)
            s.add(Implies(one[t - 1][p], PbLe([(x, 1) for x in lits], 1)))

            # If NOT one[t][p], force occ >= 2 (together with occ <= 2 -> occ == 2)
            s.add(Implies(Not(one[t - 1][p]), PbGe([(x, 1) for x in lits], 2)))

        # Exactly one period has occ(t,p) == 1
        pb_exactly_one(s, one[t - 1])


    if pin_team1_weeks > 0:
        k = min(pin_team1_weeks, W)
        for w in range(k):
            m = match_of[w][1]
            s.add(X[w][m][0])

    if use_sym:
        for m in range(M):
            s.add(X[0][m][m])

       #aw = anchor_week % W
       #for m in range(M):
       #    s.add(X[aw][m][m])

    D_var = None
    if max_diff is not None or optimize:
        if home is None:
            raise ValueError("Fairness requires with_home=True")

        # Create the optimization variable if needed
        if optimize:
            D_var = Int("D")
            # Tight bounds: W is odd => D >= 1, always D <= W
            s.add(D_var >= 1)
            s.add(D_var <= W)
        else:
            D_var = max_diff  # fixed bound (int)

        # Break global flip symmetry for home bits
        s.add(home[0][0])

        for t in range(1, n + 1):
            terms = []
            for w in range(W):
                m = match_of[w][t]
                a, b = weeks[w][m]
                if t == a:
                    terms.append(If(home[w][m], 1, 0))
                else:
                    terms.append(If(home[w][m], 0, 1))

            hg = Sum(terms)

            # |2*hg - W| <= D_var
            s.add(2 * hg - W <= D_var)
            s.add(W - 2 * hg <= D_var)

        if optimize:
            s.minimize(D_var)

    return s, weeks, X, home, W, P, D_var