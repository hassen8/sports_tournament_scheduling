# source/SMT_LIA/smt_lia_z3.py
#
# Z3-based QF-LIA decision model (no symmetry, no fairness optimization).

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "source"))
sys.path.append(str(ROOT / "source" / "SMT_LIA"))

from common.io_json import write_result_json
from smt_lia_core import build_smt_lia_model, extract_lia_schedule
from z3 import sat


def solve_smt_lia_z3(n: int):
    s, H, Weeks, Periods = build_smt_lia_model(
        n,
        use_symmetry=False,
        max_diff=None
    )
    start = time.time()
    res = s.check()
    elapsed = time.time() - start

    if res != sat:
        return None, H, Weeks, Periods, elapsed

    return s.model(), H, Weeks, Periods, elapsed


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python smt_lia_z3.py <n>")
        sys.exit(1)

    n = int(sys.argv[1])

    model, H, Weeks, Periods, t = solve_smt_lia_z3(n)
    OUT_DIR = ROOT / "res2" / "SMT_LIA"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / f"{n}.json"

    optimal = model is not None
    if optimal:
        sol = extract_lia_schedule(model, H, Weeks, Periods, n)
    else:
        sol = []

    write_result_json("SMT_LIA_Z3", n, json_path, t if t < 300 else 300, optimal, sol, obj=None)

    status = "sat" if optimal else "unsat/unknown"
    print(f"[SMT_LIA_Z3] n={n} result={status} time={t:.3f}s -> {json_path}")
