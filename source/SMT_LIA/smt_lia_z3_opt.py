# source/SMT_LIA/smt_lia_z3_opt.py
#
# Z3-based QF-LIA optimization model (fairness), NO symmetry.
# Uses binary_search_max_diff_lia.

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "source"))
sys.path.append(str(ROOT / "source" / "SMT_LIA"))

from common.io_json import write_result_json
from smt_lia_core import binary_search_max_diff_lia, extract_lia_schedule


def solve_smt_lia_z3_opt(n: int):
    model, best_diff, H, Weeks, Periods, proved_optimal, elapsed = binary_search_max_diff_lia(
        n,
        use_symmetry=False,
        timeout_sec=300
    )
    return model, best_diff, proved_optimal, H, Weeks, Periods, elapsed


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python smt_lia_z3_opt.py <n>")
        sys.exit(1)

    n = int(sys.argv[1])

    model, best_diff, proved_optimal, H, Weeks, Periods, t = solve_smt_lia_z3_opt(n)
    OUT_DIR = ROOT / "res2" / "SMT_LIA"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / f"{n}.json"

    if model is None:
        # Timeout / no solution found
        write_result_json("SMT_LIA_Z3_OPT", n, json_path, 300, False, [], obj=None)
        print(f"[SMT_LIA_Z3_OPT] n={n} Timeout/unknown -> {json_path}")
    else:
        sol = extract_lia_schedule(model, H, Weeks, Periods, n)
        time_capped = int(t) if t < 300 else 300
        write_result_json("SMT_LIA_Z3_OPT", n, json_path, time_capped, proved_optimal, sol, obj=best_diff)
        print(f"[SMT_LIA_Z3_OPT] n={n} result=sat best_diff={best_diff} time={t:.3f}s -> {json_path}")
