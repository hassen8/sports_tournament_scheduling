#!/usr/bin/env python3
import sys
import time
import argparse
import subprocess
from pathlib import Path
from z3 import sat, unsat

SMT_DIR = Path(__file__).resolve().parent
SRC_DIR = SMT_DIR.parent
ROOT = SRC_DIR.parent

sys.path.insert(0, str(SRC_DIR))

from io_json import write_result_json
from smt_period_core_bool import build_model
from smt2_export import write_smt2_file, per_var, home_var
from smt2_parse import parse_status, parse_get_value

TIME_LIMIT = 300
ALL_N = [6, 8, 10, 12, 14, 16, 18, 20, 22, 24]


def extract_schedule_z3(model, weeks, X, home, n):
    P = n // 2
    W = n - 1
    M = n // 2
    sol = [[None for _ in range(W)] for _ in range(P)]

    for w in range(W):
        for m in range(M):
            chosen_p = None
            for p in range(P):
                if model.evaluate(X[w][m][p], model_completion=True):
                    chosen_p = p
                    break
            if chosen_p is None:
                continue
            a, b = weeks[w][m]
            if home is None:
                sol[chosen_p][w] = [a, b]
            else:
                hv = bool(model.evaluate(home[w][m], model_completion=True))
                sol[chosen_p][w] = [a, b] if hv else [b, a]

    for p in range(P):
        for w in range(W):
            if sol[p][w] is None:
                return []
    return sol


def decode_schedule_env(env, weeks, W, P, with_home: bool):
    sol = [[None for _ in range(W)] for _ in range(P)]

    for w in range(W):
        for m in range(P):
            pv = env.get(per_var(w, m), None)
            if pv is None:
                return []
            if not (0 <= int(pv) < P):
                return []
            a, b = weeks[w][m]
            if not with_home:
                sol[int(pv)][w] = [a, b]
            else:
                hv = bool(env.get(home_var(w, m), True))
                sol[int(pv)][w] = [a, b] if hv else [b, a]

    for p in range(P):
        for w in range(W):
            if sol[p][w] is None:
                return []
    return sol


def run_external(backend: str, smt2_path: Path, timeout_s: int):
    if backend == "cvc5":
        cmd = ["cvc5", "--lang", "smt2", "--produce-models", str(smt2_path)]
    elif backend == "opensmt":
        cmd = ["opensmt", str(smt2_path)]
    else:
        raise ValueError(f"Unknown external backend: {backend}")

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    return proc.stdout, proc.stderr


def run_one(
    n: int,
    sym: bool,
    pin_team1_weeks: int,
    *,
    max_diff=None,
    backend: str = "z3",
    z3_opt: bool = False,
):
    """
    Semantics (as you requested):
      - backend=="z3" and z3_opt==True: use Z3 Optimize() and minimize D (no max_diff feasibility).
      - backend=="z3" and z3_opt==False: plain decision model (no fairness vars).
      - backend in {"cvc5","opensmt"}: decision if max_diff is None, else feasibility with fixed max_diff.
    """
    t_start = time.time()

    if backend == "z3":
        s, weeks, X, home, W, P, D_var = build_model(
            n=n,
            use_sym=sym,
            anchor_week=0,
            # Only create home/fairness constraints when doing Z3 optimization
            with_home=True if z3_opt else False,
            # For Z3 optimization, max_diff is not used (we minimize internal D)
            max_diff=None,
            optimize=True if z3_opt else False,
            timeout_ms=TIME_LIMIT * 1000,
            pin_team1_weeks=pin_team1_weeks,
        )

        r = s.check()

        if r == sat:
            model = s.model()
            sol = extract_schedule_z3(model, weeks, X, home, n)
            elapsed = min(time.time() - t_start, TIME_LIMIT)

            if z3_opt:
                # optimization case: return D*
                Dstar = model.evaluate(D_var, model_completion=True).as_long()
                return (elapsed, "sat", sol, Dstar) if sol else (TIME_LIMIT, "timeout", [], None)

            return (elapsed, "sat", sol, None) if sol else (TIME_LIMIT, "timeout", [], None)

        if r == unsat:
            elapsed = min(time.time() - t_start, TIME_LIMIT)
            return elapsed, "unsat", [], None

        elapsed = min(time.time() - t_start, TIME_LIMIT)
        return elapsed, "timeout", [], None

    # External solvers path (SMT-LIB)
    tmp_dir = ROOT / "res" / "SMT" / "smt2"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    label = (
        f"{backend}_{'opt' if max_diff is not None else 'dec'}"
        f"{'_sb' if sym else ''}"
        f"{'_pin'+str(pin_team1_weeks) if pin_team1_weeks>0 else ''}"
        f"{'_D'+str(max_diff) if max_diff is not None else ''}"
    )
    smt2_path = tmp_dir / f"{label}_n{n}.smt2"

    t_start = time.time()

    out_path, weeks, W, P = write_smt2_file(
        n=n,
        out_path=smt2_path,
        use_sym=sym,
        with_home=(max_diff is not None),
        max_diff=max_diff,
        add_implied_exact_counts=True,
        add_team1_pins=pin_team1_weeks,
        fix_home_sym=True,
    )

    try:
        stdout, stderr = run_external(backend, out_path, TIME_LIMIT)
    except subprocess.TimeoutExpired:
        return TIME_LIMIT, "timeout", []
    except FileNotFoundError:
        return TIME_LIMIT, "timeout", []

    st = parse_status(stdout)

    if st == "sat":
        env = parse_get_value(stdout)
        sol = decode_schedule_env(env, weeks, W, P, with_home=(max_diff is not None))
        elapsed = time.time() - t_start
        elapsed = min(elapsed, TIME_LIMIT)
        return (elapsed, "sat", sol) if sol else (TIME_LIMIT, "timeout", [])

    if st == "unsat":
        elapsed = time.time() - t_start
        elapsed = min(elapsed, TIME_LIMIT)
        return elapsed, "unsat", []

    return TIME_LIMIT, "timeout", []


def build_approaches(selected_backends, selected_modes, selected_sb, selected_pins, maxD):
    approaches = []
    for backend in selected_backends:
        for mode in selected_modes:
            for sb in selected_sb:
                for pin in selected_pins:
                    approaches.append(
                        {
                            "backend": backend,
                            "opt": (mode == "opt"),
                            "sym": bool(sb),
                            "pin": int(pin),
                            "maxD": int(maxD),
                        }
                    )
    return approaches


def key_for(cfg, D=None):
    backend = cfg["backend"].upper()
    pin = cfg["pin"]
    sym = cfg["sym"]
    if cfg["opt"]:
        k = f"SMT_{backend}_BOOL_OPT"
        if sym:
            k += "_SB"
        if pin > 0:
            k += f"_pin1w{pin}"
        if D is not None:
            k += f"_D{D}"
        return k
    else:
        k = f"SMT_{backend}_DECISION"
        if sym:
            k += "_SB"
        if pin > 0:
            k += f"_pin1w{pin}"
        return k


def parse_csv_ints(s: str):
    out = []
    for part in s.split(","):
        part = part.strip()
        if part == "":
            continue
        out.append(int(part))
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", type=int, default=0, help="n teams (0 => run all default sizes)")

    parser.add_argument("--sym", action="store_true", help="enable symmetry breaking")
    parser.add_argument("--pin-team1", type=int, default=0, help="pin team 1 match to period 0 for first k weeks")
    parser.add_argument("--backend", type=str, default="z3", choices=["z3", "cvc5", "opensmt"], help="solver backend")

    parser.add_argument("--opt", action="store_true", help="run fairness optimization (z3 uses Optimize; externals sweep max_diff)")
    parser.add_argument("--maxD", type=int, default=1, help="maximum max_diff to try when --opt is enabled (externals only)")

    parser.add_argument("--all", action="store_true", help="run all combinations")
    parser.add_argument("--backends", type=str, default="", help="comma-separated backends: z3,cvc5,opensmt")
    parser.add_argument("--modes", type=str, default="", help="comma-separated modes: decision,opt")
    parser.add_argument("--sb", type=int, choices=[0, 1], default=None, help="restrict SB off/on")
    parser.add_argument("--pins", type=str, default="", help="comma-separated pin values, e.g. 0,1,2")
    parser.add_argument("--models", type=str, default="", help="comma-separated exact keys to run")

    args = parser.parse_args()

    if args.n == 0 and not args.all and not args.models.strip():
        args.all = True

    N_VALUES = ALL_N if args.n == 0 else [args.n]

    out_dir = ROOT / "res" / "SMT"
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.models.strip():
        wanted = [k.strip() for k in args.models.split(",") if k.strip()]
        selected = []
        for k in wanted:
            cfg = {"backend": None, "opt": None, "sym": False, "pin": 0, "maxD": int(args.maxD)}
            if "_BOOL_OPT" in k:
                cfg["opt"] = True
            elif "_DECISION" in k:
                cfg["opt"] = False
            else:
                continue

            if "_Z3_" in k:
                cfg["backend"] = "z3"
            elif "_CVC5_" in k:
                cfg["backend"] = "cvc5"
            elif "_OPENSMT_" in k:
                cfg["backend"] = "opensmt"
            else:
                continue

            cfg["sym"] = ("_SB" in k)

            pin = 0
            if "_pin1w" in k:
                try:
                    pin = int(k.split("_pin1w", 1)[1].split("_", 1)[0])
                except Exception:
                    pin = 0
            cfg["pin"] = pin

            D = None
            if cfg["opt"] and "_D" in k:
                try:
                    D = int(k.rsplit("_D", 1)[1])
                except Exception:
                    D = None
            cfg["forced_D"] = D
            cfg["forced_key"] = k
            selected.append(cfg)

        if not selected:
            print("No models selected.")
            return

        for n in N_VALUES:
            json_path = out_dir / f"{n}.json"
            print(f"\n=== SMT n={n} ===")
            for cfg in selected:
                backend = cfg["backend"]
                sym = cfg["sym"]
                pin = cfg["pin"]

                if not cfg["opt"]:
                    if backend == "z3":
                        t, st, sol, _ = run_one(n, sym=sym, pin_team1_weeks=pin, max_diff=None, backend=backend, z3_opt=False)
                    else:
                        t, st, sol = run_one(n, sym=sym, pin_team1_weeks=pin, max_diff=None, backend=backend)
                    write_result_json(cfg["forced_key"], str(json_path), t, st, sol, obj=None)
                    print(f"[{cfg['forced_key']}] status={st} time={t:.3f}s")
                else:
                    # OPT
                    if backend == "z3":
                        # Ignore forced_D: z3 uses Optimize() to find D*
                        t, st, sol, Dstar = run_one(n, sym=sym, pin_team1_weeks=pin, max_diff=None, backend="z3", z3_opt=True)
                        if st == "sat":
                            write_result_json(cfg["forced_key"], str(json_path), t, "sat", sol, obj=Dstar)
                            print(f"[{cfg['forced_key']}] status=sat time={t:.3f}s obj={Dstar}")
                        else:
                            write_result_json(cfg["forced_key"], str(json_path), TIME_LIMIT, "timeout", [], obj=None)
                            print(f"[{cfg['forced_key']}] status=timeout")
                    else:
                        write_result_json(cfg["forced_key"], str(json_path), TIME_LIMIT, "timeout", [], obj=None)
                        print(f"[{cfg['forced_key']}] skipped (external optimization disabled)")
        return

    if not args.all:
        backend = args.backend
        sym = bool(args.sym)
        pins = max(0, int(args.pin_team1))

        for n in N_VALUES:
            json_path = out_dir / f"{n}.json"
            print(f"\n=== SMT solver={backend} n={n} ===")

            if args.opt:
                if backend == "z3":
                    # Z3 Optimize(): single run to get D*
                    base_key = "SMT_Z3_BOOL_OPT"
                    if sym:
                        base_key += "_SB"
                    if pins > 0:
                        base_key += f"_pin1w{pins}"

                    t, st, sol, Dstar = run_one(
                        n, sym=sym, pin_team1_weeks=pins, max_diff=None, backend="z3", z3_opt=True
                    )
                    if st == "sat":
                        write_result_json(base_key, str(json_path), t, "sat", sol, obj=Dstar)
                        print(f"[{base_key}] status=sat time={t:.3f}s obj={Dstar}")
                    else:
                        write_result_json(base_key, str(json_path), TIME_LIMIT, "timeout", [], obj=None)
                        print(f"[{base_key}] status=timeout")
                else:
                    print(f"[SMT_{backend.upper()}_BOOL_OPT] skipped (external optimization disabled)")
                    continue
            else:
                # Decision
                if backend == "z3":
                    t, st, sol, _ = run_one(n, sym=sym, pin_team1_weeks=pins, max_diff=None, backend="z3", z3_opt=False)
                else:
                    t, st, sol = run_one(n, sym=sym, pin_team1_weeks=pins, max_diff=None, backend=backend)

                key = f"SMT_{backend.upper()}_DECISION"
                if sym:
                    key += "_SB"
                if pins > 0:
                    key += f"_pin1w{pins}"
                write_result_json(key, str(json_path), t, st, sol, obj=None)
                print(f"[{key}] status={st} time={t:.3f}s")
        return

    # run-all combinations path 
    selected_backends = ["z3", "cvc5", "opensmt"]
    if args.backends.strip():
        selected_backends = [b.strip() for b in args.backends.split(",") if b.strip()]

    selected_modes = ["decision", "opt"]
    if args.modes.strip():
        selected_modes = [m.strip() for m in args.modes.split(",") if m.strip()]

    selected_sb = [0, 1] if args.sb is None else [int(args.sb)]

    selected_pins = [0, 1]
    if args.pins.strip():
        selected_pins = parse_csv_ints(args.pins)

    approaches = build_approaches(selected_backends, selected_modes, selected_sb, selected_pins, args.maxD)

    # External optimization removed: keep opt only for z3
    approaches = [cfg for cfg in approaches if (not cfg["opt"]) or cfg["backend"] == "z3"]

    for n in N_VALUES:
        json_path = out_dir / f"{n}.json"
        print(f"\n=== SMT n={n} ===")
        for cfg in approaches:
            backend = cfg["backend"]
            sym = cfg["sym"]
            pin = cfg["pin"]

            if not cfg["opt"]:
                if backend == "z3":
                    t, st, sol, _ = run_one(n, sym=sym, pin_team1_weeks=pin, max_diff=None, backend="z3", z3_opt=False)
                else:
                    t, st, sol = run_one(n, sym=sym, pin_team1_weeks=pin, max_diff=None, backend=backend)

                key = key_for(cfg)
                write_result_json(key, str(json_path), t, st, sol, obj=None)
                print(f"[{key}] status={st} time={t:.3f}s")
            else:
                if backend == "z3":
                    # Z3 Optimize(): single run, no D suffix in key_for
                    key = key_for(cfg)  # no _D
                    t, st, sol, Dstar = run_one(n, sym=sym, pin_team1_weeks=pin, max_diff=None, backend="z3", z3_opt=True)
                    if st == "sat":
                        write_result_json(key, str(json_path), t, "sat", sol, obj=Dstar)
                        print(f"[{key}] status=sat time={t:.3f}s obj={Dstar}")
                    else:
                        write_result_json(key, str(json_path), TIME_LIMIT, "timeout", [], obj=None)
                        print(f"[{key}] status=timeout")
                else:
                    key = key_for(cfg)
                    write_result_json(key, str(json_path), TIME_LIMIT, "timeout", [], obj=None)
                    print(f"[{key}] skipped (external optimization disabled)")


if __name__ == "__main__":
    main()
