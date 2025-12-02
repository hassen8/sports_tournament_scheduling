#!/usr/bin/env python3
import sys
from itertools import combinations

# Global CNF state
clauses = []
var_index = {}
reverse_var = []
next_var = 1


def new_var(name: str) -> int:
    global next_var
    if name in var_index:
        return var_index[name]
    var_index[name] = next_var
    reverse_var.append(name)
    next_var += 1
    return var_index[name]


def add_clause(lits):
    clauses.append(lits)


def exactly_one(lits):
    if not lits:
        return
    # at least one
    add_clause(lits[:])
    # pairwise at most one
    for i in range(len(lits)):
        for j in range(i + 1, len(lits)):
            add_clause([-lits[i], -lits[j]])


def at_most_k(lits, k):
    if k >= len(lits):
        return
    if k == 1:
        for i in range(len(lits)):
            for j in range(i + 1, len(lits)):
                add_clause([-lits[i], -lits[j]])
        return
    if k == 2:
        for (a, b, c) in combinations(lits, 3):
            add_clause([-a, -b, -c])


def build_dimacs(n: int, use_sym: bool = False):
    """
    Build DIMACS CNF encoding for STS with n teams.
    Populates globals: clauses, reverse_var, next_var.
    """
    global clauses, var_index, reverse_var, next_var
    clauses = []
    var_index = {}
    reverse_var = []
    next_var = 1

    if n % 2 != 0:
        sys.exit("n must be even")

    periods = n // 2
    weeks = n - 1

    teams = range(1, n + 1)
    Periods = range(periods)
    Weeks = range(weeks)

    def M(i, j, p, w):
        if i < j:
            name = f"M_{i}_{j}_{p}_{w}"
        else:
            name = f"M_{j}_{i}_{p}_{w}"
        return new_var(name)

    # 1) Each pair plays exactly once over all (p,w).
    for i in teams:
        for j in teams:
            if i < j:
                lits = [M(i, j, p, w) for p in Periods for w in Weeks]
                exactly_one(lits)

    # 2) Each team plays exactly once per week.
    for t in teams:
        for w in Weeks:
            lits = []
            for p in Periods:
                for opp in teams:
                    if opp == t:
                        continue
                    i, j = (t, opp) if t < opp else (opp, t)
                    lits.append(M(i, j, p, w))
            exactly_one(lits)

    # 3) Each (period, week) has exactly one match.
    for p in Periods:
        for w in Weeks:
            lits = []
            for i in teams:
                for j in teams:
                    if i < j:
                        lits.append(M(i, j, p, w))
            exactly_one(lits)

    # 4) Each team appears at most twice in the same period.
    for t in teams:
        for p in Periods:
            lits = []
            for opp in teams:
                if opp == t:
                    continue
                i, j = (t, opp) if t < opp else (opp, t)
                for w in Weeks:
                    lits.append(M(i, j, p, w))
            at_most_k(lits, 2)

    # Symmetry breaking (same idea as sat_core)
    if use_sym:
        # SB1: Fix week 0 as (1,2), (3,4), ...
        for p in Periods:
            i = 2 * p + 1
            j = 2 * p + 2
            if j <= n:
                add_clause([M(i, j, p, 0)])

        # SB2: Team 1 plays opponent (w+2) in week w.
        for w in Weeks:
            opp = w + 2
            if opp <= n:
                add_clause([M(1, opp, p, w) for p in Periods])


def get_reverse_map():
    return reverse_var[:]

if __name__ == "__main__":
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("n", type=int)
    parser.add_argument("--sym", action="store_true")
    args = parser.parse_args()

    build_dimacs(args.n, args.sym)

    out_dir = Path("res/SAT/dimacs")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{args.n}.cnf"

    with open(out_file, "w") as f:
        f.write(f"p cnf {next_var-1} {len(clauses)}\n")
        for clause in clauses:
            f.write(" ".join(str(l) for l in clause) + " 0\n")

    print(f"[DIMACS] Wrote {out_file} with {next_var-1} vars and {len(clauses)} clauses")
