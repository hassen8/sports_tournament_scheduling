# source/SAT/sat_wcnf.py
#
# Weighted Partial MaxSAT exporter for the explicit HOME/AWAY SAT model.
# Produces a WCNF file:
#   hard clauses = scheduling constraints
#   soft clauses = fairness (minimize home-game imbalance)
#
# Output: res/SAT/wcnf/<n>.wcnf

import sys
import argparse
from itertools import combinations
from pathlib import Path


class WCNFBuilder:
    def __init__(self):
        self.var_index = {}
        self.hard = []
        self.soft = []
        self.next_var = 1

    def v(self, key):
        if key not in self.var_index:
            self.var_index[key] = self.next_var
            self.next_var += 1
        return self.var_index[key]

    def add_hard(self, lits):
        self.hard.append(lits)

    def add_soft(self, lit, weight=1):
        self.soft.append((weight, [lit]))

    def exactly_one(self, vars_list):
        if not vars_list:
            return
        # at least one
        self.add_hard(vars_list[:])
        # at most one (pairwise)
        for i in range(len(vars_list)):
            for j in range(i + 1, len(vars_list)):
                self.add_hard([-vars_list[i], -vars_list[j]])

    def at_most_k(self, vars_list, k):
        if len(vars_list) <= k:
            return
        # k = 2 only (sufficient here)
        from itertools import combinations
        for a, b, c in combinations(vars_list, 3):
            self.add_hard([-a, -b, -c])


def build_wcnf_home_away(n, use_symmetry=False):
    if n % 2 != 0:
        raise ValueError("n must be even")

    builder = WCNFBuilder()

    periods = n // 2
    weeks = n - 1
    teams = range(1, n + 1)
    Weeks = range(1, weeks + 1)
    Periods = range(1, periods + 1)

    def H(i, j, p, w):
        return builder.v(("H", i, j, p, w))

    # 1) Slot: exactly one match per (p, w)
    for p in Periods:
        for w in Weeks:
            lits = []
            for i, j in combinations(teams, 2):
                lits.append(H(i, j, p, w))
                lits.append(H(j, i, p, w))
            builder.exactly_one(lits)

    # 2) Pair: each unordered pair meets exactly once
    for i, j in combinations(teams, 2):
        lits = []
        for p in Periods:
            for w in Weeks:
                lits.append(H(i, j, p, w))
                lits.append(H(j, i, p, w))
        builder.exactly_one(lits)

    # 3) Weekly: each team plays exactly once per week
    for t in teams:
        for w in Weeks:
            lits = []
            for p in Periods:
                for opp in teams:
                    if opp == t:
                        continue
                    lits.append(H(t, opp, p, w))
                    lits.append(H(opp, t, p, w))
            builder.exactly_one(lits)

    # 4) Period: at most twice per period per team
    for t in teams:
        for p in Periods:
            lits = []
            for w in Weeks:
                for opp in teams:
                    if opp != t:
                        lits.append(H(t, opp, p, w))
                        lits.append(H(opp, t, p, w))
            builder.at_most_k(lits, 2)

    # 5) Symmetry breaking (optional)
    if use_symmetry:
        # Week 1 canonical pairs: (1,2), (3,4), ...
        for k in Periods:
            i = 2 * k - 1
            j = 2 * k
            if j <= n:
                builder.add_hard([H(i, j, k, 1), H(j, i, k, 1)])

        # Team 1 opponent sequence
        for w in Weeks:
            opp = w + 1
            if opp <= n:
                lits = []
                for p in Periods:
                    lits.append(H(1, opp, p, w))
                    lits.append(H(opp, 1, p, w))
                builder.add_hard(lits)

    # 6) Soft fairness clauses: reward "i is home vs j"
    for i in teams:
        for j in teams:
            if i == j:
                continue
            for p in Periods:
                for w in Weeks:
                    builder.add_soft(H(i, j, p, w), weight=1)

    return builder


def write_wcnf(builder, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)

    nvars = len(builder.var_index)
    nclauses = len(builder.hard) + len(builder.soft)
    top = sum(w for w, _ in builder.soft) + 1

    with path.open("w", encoding="utf-8") as f:
        f.write(f"p wcnf {nvars} {nclauses} {top}\n")
        # hard clauses
        for clause in builder.hard:
            f.write(f"{top} " + " ".join(map(str, clause)) + " 0\n")
        # soft clauses
        for weight, clause in builder.soft:
            f.write(f"{weight} " + " ".join(map(str, clause)) + " 0\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("n", type=int)
    parser.add_argument("--sym", action="store_true")
    args = parser.parse_args()

    builder = build_wcnf_home_away(args.n, use_symmetry=args.sym)
    out = Path("res/SAT/wcnf") / f"{args.n}.wcnf"
    write_wcnf(builder, out)
    print(f"WCNF for n={args.n} (sym={args.sym}) written to {out}")
