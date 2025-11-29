# source/SAT/sat_dimacs.py
#
# DIMACS exporter for the explicit HOME/AWAY SAT model (same as sat_core.py).
# 
# Supports:
#   - decision model (no symmetry)
#   - decision + symmetry breaking (--sym flag)
#
# Writes CNF to: res/SAT/dimacs/<n>.cnf
#
# Variables:
#   H_i_j_Pp_Ww  → team i plays at home vs j away in period p, week w
#
# Constraints:
#   1) Each (period, week) has exactly one match
#   2) Each unordered pair {i,j} meets exactly once (in some period/week, dir free)
#   3) Each team plays exactly once per week
#   4) Each team appears at most twice in the same period
#   5) Optional symmetry breaking:
#        SB1: Week 1 fixed to (1,2), (3,4), etc.
#        SB2: Team 1 opponent ordering: week w → opponent = w+1

import sys
import argparse
from itertools import combinations
from pathlib import Path


# =======================================
# DIMACS Helpers
# =======================================

class CNFBuilder:
    def __init__(self):
        self.var_index = {}
        self.clauses = []
        self.next_var = 1

    def v(self, key):
        """Get/create DIMACS variable ID."""
        if key not in self.var_index:
            self.var_index[key] = self.next_var
            self.next_var += 1
        return self.var_index[key]

    def add_clause(self, lits):
        """Add a clause: lits is list of integers (positive or negative)."""
        if len(lits) == 0:
            return
        self.clauses.append(lits)

    def exactly_one(self, var_list):
        """Exactly 1 variable is true."""
        # At least one
        self.add_clause(list(var_list))
        # At most one (pairwise)
        for i in range(len(var_list)):
            for j in range(i+1, len(var_list)):
                self.add_clause([-var_list[i], -var_list[j]])

    def at_most_k(self, var_list, k):
        """At most k true variables."""
        if k >= len(var_list):
            return  # no-op
        # Simple triple-forbid for k=2 (STS requires ≤2)
        if k == 2:
            for a, b, c in combinations(var_list, 3):
                self.add_clause([-a, -b, -c])
        else:
            raise NotImplementedError("Only k=2 supported here.")


# Build CNF
def build_dimacs_home_away(n, use_symmetry=False):
    """
    Build DIMACS CNF for the SAT model.
    """
    if n % 2 != 0:
        raise ValueError("n must be even")

    builder = CNFBuilder()

    periods = n // 2
    weeks = n - 1
    teams = list(range(1, n+1))
    Weeks = list(range(1, weeks+1))
    Periods = list(range(1, periods+1))

    def H(i, j, p, w):
        """DIMACS var for home/away match."""
        return builder.v(("H", i, j, p, w))

    # 1) Slot constraints: exactly one match per (p, w)
    
    for p in Periods:
        for w in Weeks:
            lits = []
            for i, j in combinations(teams, 2):
                # two possible directions
                lits.append(H(i, j, p, w))
                lits.append(H(j, i, p, w))
            builder.exactly_one(lits)

    # 2) Pair constraints: each {i,j} meets exactly once
    
    for i, j in combinations(teams, 2):
        lits = []
        for p in Periods:
            for w in Weeks:
                lits.append(H(i, j, p, w))
                lits.append(H(j, i, p, w))
        builder.exactly_one(lits)

    # 3) Weekly constraint: each team plays exactly once per week
    for t in teams:
        for w in Weeks:
            lits = []
            for p in Periods:
                for opp in teams:
                    if opp == t: 
                        continue
                    lits.append(H(t, opp, p, w))   # t home vs opp
                    lits.append(H(opp, t, p, w))   # t away at opp
            builder.exactly_one(lits)

    # 4) At-most-two per period per team
    for t in teams:
        for p in Periods:
            lits = []
            for w in Weeks:
                for opp in teams:
                    if opp != t:
                        lits.append(H(t, opp, p, w))
                        lits.append(H(opp, t, p, w))
            builder.at_most_k(lits, 2)

    # 5) SYMMETRY BREAKING 
    
    if use_symmetry:

        # SB1: Fix week 1: period k → match (2k-1, 2k), direction free
        for k in Periods:
            i = 2*k - 1
            j = 2*k
            if j <= n:
                builder.add_clause([
                    H(i, j, k, 1),
                    H(j, i, k, 1)
                ])

        # SB2: team 1 opponent sequence
        for w in Weeks:
            opp = w + 1
            if opp <= n:
                lits = []
                for p in Periods:
                    lits.append(H(1, opp, p, w))
                    lits.append(H(opp, 1, p, w))
                builder.add_clause(lits)

    return builder


def write_dimacs(builder, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    num_vars = len(builder.var_index)
    num_clauses = len(builder.clauses)

    with open(path, "w") as f:
        f.write(f"p cnf {num_vars} {num_clauses}\n")
        for clause in builder.clauses:
            f.write(" ".join(str(l) for l in clause) + " 0\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("n", type=int)
    parser.add_argument("--sym", action="store_true",
                        help="Enable symmetry breaking")
    args = parser.parse_args()

    n = args.n
    use_sym = args.sym

    builder = build_dimacs_home_away(n, use_symmetry=use_sym)

    out_path = Path(f"res/SAT/dimacs/{n}.cnf")
    write_dimacs(builder, out_path)

    print(f"[SAT_DIMACS] CNF for n={n} (sym={use_sym}) written to {out_path}")
