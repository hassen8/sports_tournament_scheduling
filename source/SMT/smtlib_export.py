# source/SMT/smtlib_export.py

from pathlib import Path


def var_M(i, j, p, w):
    return f"M_{i}_{j}_P{p}_W{w}"


def var_H(i, j, p, w):
    return f"H_{i}_{j}_P{p}_W{w}"


def write_smtlib_file(n, label, use_symmetry=False, max_diff=None):
    """
    Writes a QF_LIA SMT-LIB file for SMT opt.

    label is used only for naming the file:
        e.g., SMT2, SMT2_SB, SMT2_OPT, SMT2_OPT_SB

    Returns the path to the generated .smt2 file.
    """

    periods = n // 2
    weeks = n - 1

    Teams = range(1, n + 1)
    Periods = range(periods)
    Weeks = range(weeks)

    out_dir = Path("res/SMT/smt2")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{label}_{n}.smt2"

    with open(out_path, "w") as f:
        f.write("(set-logic QF_LIA)\n")

        # Declare Boolean variables:
        # - M always
        # - H only if we are doing fairness optimization (max_diff not None)
        for i in Teams:
            for j in Teams:
                if i < j:
                    for p in Periods:
                        for w in Weeks:
                            f.write(f"(declare-fun {var_M(i,j,p,w)} () Bool)\n")
                            if max_diff is not None:
                                f.write(f"(declare-fun {var_H(i,j,p,w)} () Bool)\n")

        # Slot constraints: exactly one M per (p,w)
        for p in Periods:
            for w in Weeks:
                lits = [var_M(i, j, p, w)
                        for i in Teams for j in Teams if i < j]
                f.write(
                    "(assert (>= (+ "
                    + " ".join([f"(ite {x} 1 0)" for x in lits])
                    + ") 1))\n"
                )
                f.write(
                    "(assert (<= (+ "
                    + " ".join([f"(ite {x} 1 0)" for x in lits])
                    + ") 1))\n"
                )

        # Each pair plays exactly once
        for i in Teams:
            for j in Teams:
                if i < j:
                    lits = [var_M(i, j, p, w) for p in Periods for w in Weeks]
                    f.write(
                        "(assert (>= (+ "
                        + " ".join([f"(ite {x} 1 0)" for x in lits])
                        + ") 1))\n"
                    )
                    f.write(
                        "(assert (<= (+ "
                        + " ".join([f"(ite {x} 1 0)" for x in lits])
                        + ") 1))\n"
                    )

        # Weekly constraint
        for t in Teams:
            for w in Weeks:
                lits = []
                for p in Periods:
                    for opp in Teams:
                        if opp != t:
                            i, j = (t, opp) if t < opp else (opp, t)
                            lits.append(var_M(i, j, p, w))
                f.write(
                    "(assert (>= (+ "
                    + " ".join([f"(ite {x} 1 0)" for x in lits])
                    + ") 1))\n"
                )
                f.write(
                    "(assert (<= (+ "
                    + " ".join([f"(ite {x} 1 0)" for x in lits])
                    + ") 1))\n"
                )

        # Period constraint: team appears at most twice in given period
        for t in Teams:
            for p in Periods:
                lits = []
                for w in Weeks:
                    for opp in Teams:
                        if opp != t:
                            i, j = (t, opp) if t < opp else (opp, t)
                            lits.append(var_M(i, j, p, w))
                f.write(
                    "(assert (<= (+ "
                    + " ".join([f"(ite {x} 1 0)" for x in lits])
                    + ") 2))\n"
                )

        # Symmetry breaking
        if use_symmetry:
            # SB1
            for p in Periods:
                i = 2 * p + 1
                j = 2 * p + 2
                if j <= n:
                    f.write(f"(assert {var_M(i,j,p,0)})\n")

            # SB2
            for w in Weeks:
                opp = w + 2
                if opp <= n:
                    or_lits = []
                    for p in Periods:
                        i, j = (1, opp) if 1 < opp else (opp, 1)
                        or_lits.append(var_M(i, j, p, w))
                    f.write(f"(assert (or {' '.join(or_lits)}))\n")

        # Fairness constraints (optimization via max_diff)
        if max_diff is not None:
            total_games = weeks
            min_home = (total_games - max_diff) // 2
            max_home = (total_games + max_diff) // 2

            for t in Teams:
                pos = []
                for opp in Teams:
                    if opp == t:
                        continue
                    i, j = (t, opp) if t < opp else (opp, t)
                    for p in Periods:
                        for w in Weeks:
                            m = var_M(i, j, p, w)
                            h = var_H(i, j, p, w)

                            if i == t:
                                pos.append(f"(ite (and {m} {h}) 1 0)")
                            else:
                                pos.append(f"(ite (and {m} (not {h})) 1 0)")

                f.write(
                    "(assert (>= (+ "
                    + " ".join(pos)
                    + f") {min_home}))\n"
                )
                f.write(
                    "(assert (<= (+ "
                    + " ".join(pos)
                    + f") {max_home}))\n"
                )

        f.write("(check-sat)\n")
        f.write("(get-model)\n")

    return out_path
