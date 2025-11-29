# source/SMT/smt_z3.py
#
# Z3-based SMT decision model for STS (with home/away).
# Uses the unified SMT core (no symmetry, no optimization).
#
# Output key in JSON: "SMT_Z3_<n>"

import sys
import time
from pathlib import Path
from z3 import sat, unsat

# Make project imports work: common.io_json, SMT.smt_core
sys.path.append(str(Path(__file__).resolve().parents[1]))

from common.io_json import write_result_json
from SMT.smt_core import build_smt_model, extract_schedule


def solve_smt_z3_decision(n: int):
    """
    Decision model, NO symmetry, NO fairness optimization.

    Returns:
        res        -> 'sat' | 'unsat' | 'unknown'
        model      -> Z3 model or None
        H, Weeks, Periods
        elapsed    -> float seconds
    """
    s, H, Weeks, Periods = build_smt_model(
        n,
        use_symmetry=False,
        max_diff=None
    )

    start = time.time()
    res = s.check()
    elapsed = time.time() - start

    if res == sat:
        return "sat", s.model(), H, Weeks, Periods, elapsed
    elif res == unsat:
        return "unsat", None, H, Weeks, Periods, elapsed
    else:
        return "unknown", None, H, Weeks, Periods, elapsed


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python smt_z3.py <n>")
        sys.exit(1)

    n = int(sys.argv[1])

    res, model, H, Weeks, Periods, t = solve_smt_z3_decision(n)

    out_dir = Path("res/SMT")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{n}.json"

    # Project semantics:
    # - SAT/UNSAT within time: time = floor(actual), optimal = True
    # - Timeout/unknown: time = 300, optimal = False, sol = [], obj = None

    if res == "unknown":
        # Timeout / unknown
        write_result_json("SMT_Z3", n, str(out_path), 300, False, [], obj=None)
        print(f"[SMT_Z3] n={n} TIMEOUT/UNKNOWN (reported time=300s) -> {out_path}")
        sys.exit(0)

    if res == "unsat":
        time_int = int(t)
        write_result_json("SMT_Z3", n, str(out_path), time_int, True, [], obj=None)
        print(f"[SMT_Z3] n={n} UNSAT in {time_int}s -> {out_path}")
        sys.exit(0)

    # SAT
    sol = extract_schedule(model, n, H, Weeks, Periods)
    time_int = int(t)
    write_result_json("SMT_Z3", n, str(out_path), time_int, True, sol, obj=None)
    print(f"[SMT_Z3] n={n} SAT in {time_int}s -> {out_path}")
