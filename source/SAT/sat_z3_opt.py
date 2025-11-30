import sys, time
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from common.io_json import write_result_json
from SAT.sat_core import binary_search_max_diff, extract_schedule

if __name__ == "__main__":
    n = int(sys.argv[1])

    json_path = f"res/SAT/{n}.json"

    start = time.time()
    model, best_diff, M, H, W, P = binary_search_max_diff(
        n, use_symmetry=False, verbose=False
    )
    elapsed = time.time() - start

    if best_diff is None:
        # UNSAT case
        write_result_json(
            "z3_opt",
            json_path,
            elapsed,
            "unsat",
            [],
            None
        )
        print(f"[z3_opt] n={n} status=unsat time={elapsed:.3f}s")

    else:
        sol = extract_schedule(model, n, M, H, W, P)
        write_result_json(
            "z3_opt",
            json_path,
            elapsed,
            "sat",
            sol,
            best_diff
        )
        print(f"[z3_opt] n={n} best_diff={best_diff} status=sat time={elapsed:.3f}s")
