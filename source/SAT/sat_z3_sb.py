# source/SAT/sat_z3_sb.py

import sys, time
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from common.io_json import write_result_json

from sat_core import build_model, extract_schedule
from z3 import sat

if __name__ == "__main__":
    n = int(sys.argv[1])
    s, H, W, P = build_model(n, use_symmetry=True, max_diff=None)

    start = time.time()
    res = s.check()
    elapsed = time.time() - start

    optimal = (res == sat)
    sol = extract_schedule(s.model(), n, H, W, P) if optimal else []

    out = f"res/SAT/{n}.json"
    write_result_json("SAT_Z3_SB", n, out, elapsed, optimal, sol)

    print(f"[SAT_Z3_SB] n={n} result={res} time={elapsed:.3f}s -> {out}")
