from pathlib import Path


def var_M(i, j, p, w):
    return f"M_{i}_{j}_P{p}_W{w}"


def var_H(i, j, p, w):
    return f"H_{i}_{j}_P{p}_W{w}"


def write_smtlib_file(n, label, use_symmetry=False, max_diff=None):
    """
    Generate SMT-LIB2 file for the STS problem.
    - If max_diff is None → pure decision version
    - If max_diff is not None → fairness optimization (bounded by max_diff)
    """

    periods = n // 2
    weeks = n - 1

    Teams   = range(1, n + 1)
    Periods = range(periods)
    Weeks   = range(weeks)

    out_dir = Path("res/SMT/smt2")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{label}_{n}.smt2"

    with open(out_path, "w") as f:

      
        # HEADER
        
        f.write("(set-logic QF_LIA)\n")
        f.write("(set-option :produce-models true)\n")

        # DECLARATIONS
     
        for i in Teams:
            for j in Teams:
                if i < j:
                    for p in Periods:
                        for w in Weeks:
                            f.write(f"(declare-fun {var_M(i,j,p,w)} () Bool)\n")
                            if max_diff is not None:
                                f.write(f"(declare-fun {var_H(i,j,p,w)} () Bool)\n")

       
        # CONSTRAINTS
        

        # 1. Slot constraint: exactly one match per (p,w)
        for p in Periods:
            for w in Weeks:
                lits = [var_M(i, j, p, w)
                        for i in Teams for j in Teams if i < j]

                sum_expr = " ".join([f"(ite {x} 1 0)" for x in lits])
                f.write(f"(assert (>= (+ {sum_expr}) 1))\n")
                f.write(f"(assert (<= (+ {sum_expr}) 1))\n")

        # 2. Every pair plays exactly once
        for i in Teams:
            for j in Teams:
                if i < j:
                    lits = [var_M(i, j, p, w) for p in Periods for w in Weeks]

                    sum_expr = " ".join([f"(ite {x} 1 0)" for x in lits])
                    f.write(f"(assert (>= (+ {sum_expr}) 1))\n")
                    f.write(f"(assert (<= (+ {sum_expr}) 1))\n")

        # 3. Weekly constraint: each team plays exactly once per week
        for t in Teams:
            for w in Weeks:
                lits = []
                for p in Periods:
                    for opp in Teams:
                        if opp != t:
                            i, j = (t, opp) if t < opp else (opp, t)
                            lits.append(var_M(i, j, p, w))

                sum_expr = " ".join([f"(ite {x} 1 0)" for x in lits])
                f.write(f"(assert (>= (+ {sum_expr}) 1))\n")
                f.write(f"(assert (<= (+ {sum_expr}) 1))\n")

        # 4. Period constraint: each team appears at most twice in a period
        for t in Teams:
            for p in Periods:
                lits = []
                for w in Weeks:
                    for opp in Teams:
                        if opp != t:
                            i, j = (t, opp) if t < opp else (opp, t)
                            lits.append(var_M(i, j, p, w))

                sum_expr = " ".join([f"(ite {x} 1 0)" for x in lits])
                f.write(f"(assert (<= (+ {sum_expr}) 2))\n")

      
        # SYMMETRY BREAKING
       
        if use_symmetry:
            # SB1: fix the first week as (1,2), (3,4), ..., into their periods
            for p in Periods:
                i = 2 * p + 1
                j = 2 * p + 2
                if j <= n:
                    f.write(f"(assert {var_M(i,j,p,0)})\n")

            # SB2: team 1 faces opponent w+2 in week w, in some period
            for w in Weeks:
                opp = w + 2
                if opp <= n:
                    or_lits = []
                    for p in Periods:
                        if 1 < opp:
                            i, j = 1, opp
                        else:
                            i, j = opp, 1
                        or_lits.append(var_M(i, j, p, w))
                    f.write(f"(assert (or {' '.join(or_lits)}))\n")

      
        # FAIRNESS (if max_diff is provided)
        
        if max_diff is not None:
            total_games = weeks
            min_home = (total_games - max_diff) // 2
            max_home = (total_games + max_diff) // 2

            for t in Teams:
                terms = []

                for opp in Teams:
                    if opp == t:
                        continue

                    i, j = (t, opp) if t < opp else (opp, t)

                    for p in Periods:
                        for w in Weeks:
                            m = var_M(i, j, p, w)
                            h = var_H(i, j, p, w)

                            # team t is home iff:
                            # - i==t and H is true, OR
                            # - j==t and H is false
                            if i == t:
                                terms.append(f"(ite (and {m} {h}) 1 0)")
                            else:
                                terms.append(f"(ite (and {m} (not {h})) 1 0)")

                sum_expr = " ".join(terms)
                f.write(f"(assert (>= (+ {sum_expr}) {min_home}))\n")
                f.write(f"(assert (<= (+ {sum_expr}) {max_home}))\n")

       
        # FINAL CHECK
       
        f.write("(check-sat)\n")
        f.write("(get-model)\n")

    return out_path
