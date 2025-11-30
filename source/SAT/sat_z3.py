import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from z3 import sat, unsat
from common.io_json import write_result_json
from SAT.sat_core import build_model, extract_schedule

if __name__ == "__main__":
    n = int(sys.argv[1])

    s, M, H, W, P = build_model(n, use_symmetry=False, max_diff=None)

    start = time.time()
    res = s.check()
    elapsed = time.time() - start

    print(f"[z3_sat] n={n} status={res} time={elapsed:.3f}s")

    json_path = Path("res") / "SAT" / f"{n}.json"

    if res == sat:
        sol = extract_schedule(s.model(), n, M, H, W, P)
        status = "sat"
        obj = None
    elif res == unsat:
        sol = []
        status = "unsat"
        obj = None
    else:
        sol = []
        status = "timeout"
        obj = None

    write_result_json("z3_sat", json_path, elapsed, status, sol, obj)
