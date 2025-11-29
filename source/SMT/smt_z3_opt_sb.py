# source/SMT/smt_z3_opt_sb.py
#
# Z3-based SMT optimization model (fairness) WITH symmetry breaking.
# Uses the unified SMT core:
#   - binary_search_max_diff(use_symmetry=True)
#   - extract_schedule(...)
#
# Output key in JSON: "SMT_Z3_OPT_SB_<n>"

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from common.io_json import write_result_json
from SMT.smt_core import binary_search_max_diff, extract_schedule


def solve_smt_z3_opt_sb(n: int):
    """
    Optimization: minimize home/away imbalance (max_diff),
    WITH symmetry breaking.

    Returns:
        model          -> Z3 model or None
        best_diff      -> int or None
        proved_optimal -> True iff we proved optimality within 300s
        H, Weeks, Periods
        elapsed        -> float seconds
    """
    model, best_diff, H, Weeks, Periods, proved_optimal, elapsed = binary_search_max_diff(
        n,
        use_symmetry=True,
        time_limit=300
    )
    return model, best_diff, proved_optimal, H, Weeks, Periods, elapsed


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python smt_z3_opt_sb.py <n>")
        sys.exit(1)

    n = int(sys.argv[1])
    model, best_diff, proved_optimal, H, Weeks, Periods, t = solve_smt_z3_opt_sb(n)

    out_dir = Path("res/SMT")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{n}.json"

    # CASE 1: No model at all
    if model is None and best_diff is None:
        write_result_json("SMT_Z3_OPT_SB", n, str(out_path), 300, False, [], obj=None)
        print(f"[SMT_Z3_OPT_SB] n={n} NO SOLUTION found within 300s -> {out_path}")
        sys.exit(0)

    # CASE 2: Model found but NOT proved optimal within 300s
    if not proved_optimal:
        sol = extract_schedule(model, n, H, Weeks, Periods)
        write_result_json("SMT_Z3_OPT_SB", n, str(out_path), 300, False, sol, obj=best_diff)
        print(f"[SMT_Z3_OPT_SB] n={n} BEST-KNOWN diff={best_diff} (NOT proved optimal, hit 300s) -> {out_path}")
        sys.exit(0)

    # CASE 3: Proved optimal within 300s
    sol = extract_schedule(model, n, H, Weeks, Periods)
    time_int = int(t)
    if time_int >= 300:
        write_result_json("SMT_Z3_OPT_SB", n, str(out_path), 300, False, sol, obj=best_diff)
        print(f"[SMT_Z3_OPT_SB] n={n} FOUND optimum diff={best_diff} but elapsed={t:.3f}s >= 300, reporting as non-optimal -> {out_path}")
        sys.exit(0)

    write_result_json("SMT_Z3_OPT_SB", n, str(out_path), time_int, True, sol, obj=best_diff)
    print(f"[SMT_Z3_OPT_SB] n={n} OPTIMAL diff={best_diff} time={time_int}s -> {out_path}")
