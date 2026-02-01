#!/usr/bin/env python3
import sys, time
from pathlib import Path
from z3 import sat, unsat

SRC_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC_DIR))

from io_json import write_result_json
from smt_period_core_bool import build_model

TIME_LIMIT = 300

def extract_schedule(model, weeks, X, home, n):
    P = n // 2
    W = n - 1
    M = n // 2
    sol = [[None for _ in range(W)] for _ in range(P)]
    for w in range(W):
        for m in range(M):
            for p in range(P):
                if model.evaluate(X[w][m][p], model_completion=True):
                    a, b = weeks[w][m]
                    if home is None:
                        sol[p][w] = [a, b]
                    else:
                        hv = bool(model.evaluate(home[w][m], model_completion=True))
                        sol[p][w] = [a, b] if hv else [b, a]
    return sol

def is_full(sol):
    return sol and all(all(c is not None for c in row) for row in sol)

def solve(n, use_sym=False, anchor_week=0, time_limit_s=300):
    W = n - 1
    lo, hi = 0, W
    best_sol, best = None, None
    proved = True
    start = time.time()

    while lo <= hi:
        if time.time() - start >= time_limit_s:
            proved = False
            break
        mid = (lo + hi) // 2

        s, weeks, X, home, W2, P2 = build_model(
            n,
            use_sym=use_sym,
            anchor_week=anchor_week,
            with_home=True,
            max_diff=mid,
            timeout_ms=int((time_limit_s - (time.time() - start)) * 1000)
        )

        r = s.check()
        if r == sat:
            sol = extract_schedule(s.model(), weeks, X, home, n)
            if not is_full(sol):
                proved = False
                break
            best, best_sol = mid, sol
            hi = mid - 1
        elif r == unsat:
            lo = mid + 1
        else:
            proved = False
            break

    total = time.time() - start
    if best_sol is None:
        return total, "timeout", [], None, False

    status = "sat" if proved and total < time_limit_s else "timeout"
    return min(total, time_limit_s), status, best_sol, best, proved

if __name__ == "__main__":
    n = int(sys.argv[1])
    # opt_sb version passes anchor_weekopt version ignores it
    use_sym = ("_sb" in Path(__file__).name)
    aw = int(sys.argv[2]) if (use_sym and len(sys.argv) > 2) else 0

    t, st, sol, obj, proved = solve(n, use_sym=use_sym, anchor_week=aw, time_limit_s=TIME_LIMIT)

    out_dir = Path(__file__).resolve().parents[2] / "res" / "SMT"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{n}.json"

    key = f"SMT_Z3_BOOL_OPT{'_SB_aw'+str(aw) if use_sym else ''}"
    write_result_json(key, str(out_path), t, st, sol, obj=obj)
    print(f"[{key}] n={n} status={st} time={t:.3f}s obj={obj} proved={proved}")
