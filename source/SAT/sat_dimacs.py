#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path

# DIMACS CNF builder for Round-Robin Tournament SAT model
# Mirrors constraints used in sat_core.py
# 

# Global CNF container
clauses = []
var_index = {}
reverse_var = []
next_var = 1

def new_var(name):
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
    # at least one
    add_clause(lits[:])
    # pairwise at most one
    for i in range(len(lits)):
        for j in range(i+1, len(lits)):
            add_clause([-lits[i], -lits[j]])


def at_most_k(lits, k):
    # simple pairwise (sufficient for k=2 which is our case)
    if k >= len(lits):
        return
    if k == 1:
        # reduce to at-most-one
        for i in range(len(lits)):
            for j in range(i+1, len(lits)):
                add_clause([-lits[i], -lits[j]])
        return
    # For k=2 simple O(n^2) encoding
    # For our tournament constraint (≤2), this is fine
    # Any triple must not all be true
    from itertools import combinations
    for (a,b,c) in combinations(lits, 3):
        add_clause([-a, -b, -c])


#CNF MODEL

def build_dimacs(n, use_symmetry=False):
    global clauses, var_index, reverse_var, next_var
    clauses = []
    var_index = {}
    reverse_var = []
    next_var = 1

    if n % 2 != 0:
        sys.exit("n must be even")

    periods = n // 2
    weeks   = n - 1

    teams = range(1, n+1)
    Periods = range(periods)
    Weeks   = range(weeks)

    def M(i,j,p,w):
        if i < j:
            name = f"M_{i}_{j}_{p}_{w}"
        else:
            name = f"M_{j}_{i}_{p}_{w}"
        return new_var(name)

    def H(i,j,p,w):
        # only meaningful when generating for maxsat or fairness,
        # but defined anyway for consistency and to try later
        if i < j:
            name = f"H_{i}_{j}_{p}_{w}"
        else:
            name = f"H_{j}_{i}_{p}_{w}"
        return new_var(name)

    # 1) pair exactly once
    for i in teams:
        for j in teams:
            if i < j:
                lits = [M(i,j,p,w) for p in Periods for w in Weeks]
                exactly_one(lits)

    # 2) weekly exactly once
    for t in teams:
        for w in Weeks:
            lits = []
            for p in Periods:
                for opp in teams:
                    if opp == t: continue
                    i,j = (t,opp) if t < opp else (opp,t)
                    lits.append(M(i,j,p,w))
            exactly_one(lits)

    # 3) each slot exactly one match
    for p in Periods:
        for w in Weeks:
            lits = []
            for i in teams:
                for j in teams:
                    if i < j:
                        lits.append(M(i,j,p,w))
            exactly_one(lits)

    # 4) ≤2 matches per period per team
    for t in teams:
        for p in Periods:
            lits = []
            for opp in teams:
                if opp == t: continue
                i,j = (t,opp) if t < opp else (opp,t)
                for w in Weeks:
                    lits.append(M(i,j,p,w))
            at_most_k(lits, 2)

    # Symmetry breaking
    if use_symmetry:
        # SB1
        for p in Periods:
            i = 2*p + 1
            j = 2*p + 2
            if j <= n:
                add_clause([ M(i,j,p,0) ])
        # SB2
        for w in Weeks:
            opp = w + 2
            if opp <= n:
                add_clause([ M(1,opp,p,w) for p in Periods ])
        # SB3 (home team full symmetry)
        # omitted for pure CNF decision

    return


#main

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("n", type=int)
    parser.add_argument("--sym", action="store_true")
    args = parser.parse_args()

    n = args.n
    use_sym = args.sym

    build_dimacs(n, use_sym)

    out_dir = Path("res/SAT/dimacs")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{n}.cnf"

    with open(out_file, "w") as f:
        f.write(f"p cnf {next_var-1} {len(clauses)}\n")
        for clause in clauses:
            f.write(" ".join(str(l) for l in clause) + " 0\n")

    print(f"[DIMACS] Wrote {out_file} with {next_var-1} vars and {len(clauses)} clauses")
