# source/SAT/maxsat_decode.py
#
# Decode open-wbo MaxSAT solution for STS:
#   v <lits> ...
# into a schedule matrix using the same mapping as sat_wcnf.py

from itertools import combinations

def build_dimacs_map(n):
    """
    Reconstruct DIMACS var_id -> (i,j,p,w)
    exactly in the order used by sat_wcnf.py.
    """
    periods = n // 2
    weeks = n - 1
    teams = range(1, n+1)

    mapping = {}            # dimacs_id -> (i,j,p,w)
    dimacs_id = 1

    for p in range(1, periods+1):
        for w in range(1, weeks+1):
            for (i,j) in combinations(teams,2):
                mapping[dimacs_id] = (i,j,p,w)
                dimacs_id += 1
                mapping[dimacs_id] = (j,i,p,w)
                dimacs_id += 1

    return mapping  # has exactly n*(n-1)/2 * 2 * periods * weeks entries


def decode_maxsat_model(n, true_literals):
    """
    Input:
        n                  = number of teams
        true_literals      = set of DIMACS var_ids that are TRUE

    Output:
        schedule[period][week] = [home, away]
    """
    periods = n // 2
    weeks = n - 1

    mapping = build_dimacs_map(n)

    # init empty schedule
    schedule = [[None for _ in range(weeks)] for _ in range(periods)]

    for lit in true_literals:
        if lit <= 0:
            continue
        if lit not in mapping:
            continue

        i,j,p,w = mapping[lit]
        schedule[p-1][w-1] = [i,j]

    return schedule
