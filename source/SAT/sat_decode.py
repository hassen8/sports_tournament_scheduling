#!/usr/bin/env python3
import re

def parse_glucose_solution(output: str):
    """
    Parses Glucose SAT output and extracts variable assignments.
    Returns: dict { dimacs_var_id : True/False }
    """
    assignments = {}
    for line in output.splitlines():
        line = line.strip()
        if not line.startswith("v"):
            continue
        parts = line.split()[1:]
        for tok in parts:
            if tok == "0":
                continue
            lit = int(tok)
            assignments[abs(lit)] = (lit > 0)
    return assignments


def decode_schedule(assignments, reverse_var, n: int):
    """
    Convert DIMACS assignments to STS schedule matrix using variable names
    in reverse_var (0-indexed list of variable names).

    We only care about variables named: M_i_j_p_w
    We interpret them as: in period p, week w, teams i (home) vs j (away).

    Returns:
        sol[p][w] = [home, away]
        or None if some slot is missing -> treat as failure.
    """
    periods = n // 2
    weeks = n - 1
    sol = [[None for _ in range(weeks)] for _ in range(periods)]

    pat_M = re.compile(r"^M_(\d+)_(\d+)_(\d+)_(\d+)$")

    for vid, val in assignments.items():
        if not val:
            continue

        idx = vid - 1
        if idx < 0 or idx >= len(reverse_var):
            continue

        name = reverse_var[idx]
        m = pat_M.match(name)
        if not m:
            continue

        i = int(m.group(1))
        j = int(m.group(2))
        p = int(m.group(3))
        w = int(m.group(4))

        # One match per (p,w) by construction, so just assign:
        sol[p][w] = [i, j]

    # any None will be decoding failure
    for p in range(periods):
        for w in range(weeks):
            if sol[p][w] is None:
                return None

    return sol
