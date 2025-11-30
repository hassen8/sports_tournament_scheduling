# source/SMT/smt_decode.py
#
# Decode an SMT-LIB model (from Yices, OpenSMT, etc.)
# into the STS schedule format:
#   sol[period][week] = [home, away]
#
# Variables follow the naming used in smtlib_export.py:
#   M_i_j_Pp_Ww : Bool  (unordered match between teams i<j)
#   H_i_j_Pp_Ww : Bool  (direction: True = i home, False = j home)

import re


def decode_smt_model(model_str: str, n: int):
    """
    Parse SMT solver model output and reconstruct schedule.

    Args:
        model_str : stdout of the SMT solver (string)
        n         : number of teams (even)

    Returns:
        sol : list[period][week] = [home, away]
    """

    periods = n // 2
    weeks = n - 1

    # Maps (i,j,p,w) -> bool
    M_vals = {}
    H_vals = {}

    lines = model_str.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("(define-fun"):
            parts = line.replace("(", " ").replace(")", " ").split()
            
            name = None
            if len(parts) >= 3:
                name = parts[2] if parts[1] == "define-fun" else parts[1]

            if not name:
                i += 1
                continue

            # Find value (true/false) in subsequent lines, including possibly this one)
            val = None
            j = i
            while j < len(lines):
                l2 = lines[j]
                if " true" in l2 or l2.strip().endswith("true"):
                    val = True
                    break
                if " false" in l2 or l2.strip().endswith("false"):
                    val = False
                    break
                if ")" in l2:
                    break
                j += 1

            if val is None:
                i = j + 1
                continue

            # Parse names of form M_i_j_Pp_Ww or H_i_j_Pp_Ww
            if name.startswith("M_") or name.startswith("H_"):
              
                m = re.match(r"([MH])_(\d+)_(\d+)_P(\d+)_W(\d+)", name)
                if m:
                    kind = m.group(1)
                    ti = int(m.group(2))
                    tj = int(m.group(3))
                    p = int(m.group(4))
                    w = int(m.group(5))
                    key = (ti, tj, p, w)
                    if kind == "M":
                        M_vals[key] = val
                    else:
                        H_vals[key] = val

            i = j + 1
        else:
            i += 1

    # Build solution matrix
    sol = [[None for _ in range(weeks)] for _ in range(periods)]

    # For every M that is true, set the match at (p,w)
    for (ti, tj, p, w), mv in M_vals.items():
        if not mv:
            continue
        if p < 0 or p >= periods or w < 0 or w >= weeks:
            continue

        # Direction: default i home, j away
        home, away = ti, tj

        key = (ti, tj, p, w)
        if key in H_vals:
            hv = H_vals[key]
            if hv is False:
                home, away = tj, ti

        sol[p][w] = [home, away]

    # There should be exactly one match per (p,w), but if some are None
    # we still return the partial structure, hopefully the caller/solution checker will catch it).
    return sol
