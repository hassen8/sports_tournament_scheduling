import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from common.io_json import write_result_json
from SAT.sat_core import binary_search_max_diff, extract_schedule

if __name__ == "__main__":
    n = int(sys.argv[1])

    start = time.time()
    model, best_diff, M, H, W, P = binary_search_max_diff(n, use_symmetry=True, verbose=False)
    elapsed = time.time() - start

    if model is None:
        status = "unsat"
        obj = None
        sol = []
        print(f"[z3_opt_sb] n={n} status=unsat time={elapsed:.3f}s")
    else:
        status = "sat"
        obj = int(best_diff)
        sol = extract_schedule(model, n, M, H, W, P)
        print(f"[z3_opt_sb] n={n} best_diff={best_diff} status=sat time={elapsed:.3f}s")

    json_path = Path("res") / "SAT" / f"{n}.json"
    write_result_json("z3_opt_sb", json_path, elapsed, status, sol, obj)
