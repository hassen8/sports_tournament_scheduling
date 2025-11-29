# source/SAT/sat_z3_opt_sb.py

import sys, time
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from common.io_json import write_result_json

from sat_core import binary_search_max_diff, extract_schedule

if __name__ == "__main__":
    n = int(sys.argv[1])

    start = time.time()
    model, best_diff, H, W, P = binary_search_max_diff(n, use_symmetry=True)
    elapsed = time.time() - start

    optimal = model is not None
    sol = extract_schedule(model, n, H, W, P) if optimal else []

    out = f"res/SAT/{n}.json"
    write_result_json("SAT_Z3_OPT_SB", n, out, elapsed, optimal, sol, obj=best_diff)

    print(f"[SAT_Z3_OPT_SB] n={n} result={'sat' if optimal else 'unsat'} "
          f"best_diff={best_diff} time={elapsed:.3f}s -> {out}")
