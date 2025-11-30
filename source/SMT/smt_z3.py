# source/SMT/smt_z3.py
#
# Z3-based SMT decision model for STS (with home/away).
# Uses the unified SMT core (no symmetry, no optimization).
#
# JSON approach key: "SMT_Z3"

import sys
import time
from pathlib import Path
from z3 import sat, unsat

sys.path.append(str(Path(__file__).resolve().parents[1]))

from common.io_json import write_result_json
from SMT.smt_core import build_smt_model, extract_schedule


def solve_smt_z3_decision(n: int):
    s, M, H, Weeks, Periods = build_smt_model(
        n,
        use_symmetry=False,
        max_diff=None
    )

    start = time.time()
    try:
        res_z3 = s.check()
    except KeyboardInterrupt:
        return "interrupted", None, M, H, Weeks, Periods, time.time() - start

    elapsed = time.time() - start

    if res_z3 == sat:
        return "sat", s.model(), M, H, Weeks, Periods, elapsed
    elif res_z3 == unsat:
        return "unsat", None, M, H, Weeks, Periods, elapsed
    else:
        return "unknown", None, M, H, Weeks, Periods, elapsed


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python smt_z3.py <n>")
        sys.exit(1)

    n = int(sys.argv[1])

    res, model, M, H, Weeks, Periods, t = solve_smt_z3_decision(n)

    out_dir = Path("res/SMT")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{n}.json"

    # INTERRUPTED
    if res == "interrupted":
        write_result_json(
            "SMT_Z3",
            str(out_path),
            300,
            "timeout",
            [],
            obj=None
        )
        print(f"[SMT_Z3] n={n} INTERRUPTED at {t:.3f}s -> {out_path}")
        sys.exit(0)

    # UNKNOWN / TIMEOUT
    if res == "unknown":
        write_result_json(
            "SMT_Z3",
            str(out_path),
            300,
            "timeout",
            [],
            obj=None
        )
        print(f"[SMT_Z3] n={n} TIMEOUT in {t:.3f}s -> {out_path}")
        sys.exit(0)

    # UNSAT
    if res == "unsat":
        write_result_json(
            "SMT_Z3",
            str(out_path),
            t,
            "unsat",
            [],
            obj=None
        )
        print(f"[SMT_Z3] n={n} UNSAT in {t:.3f}s -> {out_path}")
        sys.exit(0)

    # SAT
    sol = extract_schedule(model, n, M, H, Weeks, Periods)

    write_result_json(
        "SMT_Z3",
        str(out_path),
        t,
        "sat",
        sol,
        obj=None
    )

    print(f"[SMT_Z3] n={n} SAT in {t:.3f}s -> {out_path}")
