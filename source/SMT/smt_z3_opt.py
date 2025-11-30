# source/SMT/smt_z3_opt.py
#
# Z3-based SMT optimization model (fairness), NO symmetry.
# Uses time-limited binary search via smt_core.
#
# JSON approach key: "SMT_Z3_OPT"

import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from common.io_json import write_result_json
from SMT.smt_core import binary_search_max_diff, extract_schedule


def solve_smt_z3_opt(n: int):
    """
    Minimizes fairness objective (max_diff) using binary search.
    Hard 300s global time limit enforced inside binary_search_max_diff.

    Returns:
        model, best_diff, proved_optimal, M, H, Weeks, Periods, elapsed
    """
    (model,
     best_diff,
     M,
     H,
     Weeks,
     Periods,
     proved_optimal,
     elapsed) = binary_search_max_diff(
         n,
         use_symmetry=False,
         time_limit=300
     )

    return model, best_diff, proved_optimal, M, H, Weeks, Periods, elapsed


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python smt_z3_opt.py <n>")
        sys.exit(1)

    n = int(sys.argv[1])

    (model,
     best_diff,
     proved_optimal,
     M,
     H,
     Weeks,
     Periods,
     t) = solve_smt_z3_opt(n)

    out_dir = Path("res/SMT")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{n}.json"

    # CASE A: No model found at all within limit
    if model is None and best_diff is None:
        write_result_json(
            "SMT_Z3_OPT",
            str(out_path),
            t,
            "timeout",
            [],
            obj=None
        )
        print(f"[SMT_Z3_OPT] n={n} TIMEOUT in {t:.3f}s -> {out_path}")
        sys.exit(0)

    # Extract schedule once we have a model
    sol = extract_schedule(model, n, M, H, Weeks, Periods)

    # CASE B: Found a solution but NOT proved optimal within 300s
    if not proved_optimal:
        write_result_json(
            "SMT_Z3_OPT",
            str(out_path),
            t,
            "timeout",
            sol,
            obj=best_diff
        )
        print(f"[SMT_Z3_OPT] n={n} BEST diff={best_diff} TIMEOUT at {t:.3f}s -> {out_path}")
        sys.exit(0)

    # CASE C: Optimal solution proved
    time_int = int(t)

    if time_int >= 300:
        # Safety fallback — treat as timeout/unknown
        write_result_json(
            "SMT_Z3_OPT",
            str(out_path),
            t,
            "timeout",
            sol,
            obj=best_diff
        )
        print(f"[SMT_Z3_OPT] n={n} BEST diff={best_diff} TIMEOUT (elapsed={t:.3f}s) -> {out_path}")
        sys.exit(0)

    write_result_json(
        "SMT_Z3_OPT",
        str(out_path),
        t,
        "sat",
        sol,
        obj=best_diff
    )
    print(f"[SMT_Z3_OPT] n={n} OPTIMAL diff={best_diff} in {t:.3f}s -> {out_path}")
