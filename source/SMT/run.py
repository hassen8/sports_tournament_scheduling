#!/usr/bin/env python3

import sys
import subprocess
import time
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "source"))

from common.io_json import write_result_json
from SMT.smt_decode import decode_smt_model
from SMT.smtlib_export import write_smtlib_file

# External solver (ONLY OPENSMT)
OPENSMT = "opensmt"
TIME_LIMIT = 300

# Python Z3 solvers
Z3_MODELS = {
    "SMT_Z3":        {"script": "smt_z3.py"},
    "SMT_Z3_SB":     {"script": "smt_z3_sb.py"},
    "SMT_Z3_OPT":    {"script": "smt_z3_opt.py"},
    "SMT_Z3_OPT_SB": {"script": "smt_z3_opt_sb.py"},
}

# SMT-LIB variants
SMTLIB_VARIANTS = {
    "SMT2":        {"sym": False, "opt": False},
    "SMT2_SB":     {"sym": True,  "opt": False},
    "SMT2_OPT":    {"sym": False, "opt": True},
    "SMT2_OPT_SB": {"sym": True,  "opt": True},
}


def load_json(path):
    if not path.exists():
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return {}


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def run_python_model(name, cfg, n):
    script = ROOT / "source" / "SMT" / cfg["script"]
    try:
        subprocess.run(
            [sys.executable, str(script), str(n)],
            text=True,
            capture_output=True,
            timeout=300
        )
    except subprocess.TimeoutExpired:
        return None

    json_path = ROOT / "res" / "SMT" / f"{n}.json"
    return load_json(json_path)


def is_full_schedule(sol):
    if not sol:
        return False
    for row in sol:
        if row is None:
            return False
        for cell in row:
            if cell is None:
                return False
    return True


def call_external_solver_once(solver_cmd, smt2_path, remaining_time):
    start = time.time()
    try:
        proc = subprocess.run(
            [solver_cmd, str(smt2_path)],
            text=True,
            capture_output=True,
            timeout=max(1, int(remaining_time))
        )
        elapsed = time.time() - start
        out = proc.stdout.strip()
    except subprocess.TimeoutExpired:
        return TIME_LIMIT, "", "timeout"

    if not out:
        return elapsed, "", "unknown"

    first = out.split()[0].lower()
    if first.startswith("unsat"):
        return elapsed, out, "unsat"
    if first.startswith("sat"):
        return elapsed, out, "sat"

    return elapsed, out, "unknown"


def run_external_decision(solver_cmd, smt2_path, n):
    elapsed, out, status = call_external_solver_once(
        solver_cmd,
        smt2_path,
        remaining_time=TIME_LIMIT
    )

    # ================================
    # CORRECT UNSAT HANDLING
    # ================================
    if status == "unsat":
        return {
            "time": int(elapsed),
            "actual_time": elapsed,
            "status": "unsat",
            "sol": [],          # UNSAT = solved, empty schedule
            "obj": None
        }

    if status != "sat":
        return {
            "time": TIME_LIMIT,
            "actual_time": elapsed,
            "status": "timeout",
            "sol": [],
            "obj": None
        }

    # SAT → decode
    sol = decode_smt_model(out, n)
    if not is_full_schedule(sol):
        return {
            "time": TIME_LIMIT,
            "actual_time": elapsed,
            "status": "timeout",
            "sol": [],
            "obj": None
        }

    return {
        "time": int(elapsed),
        "actual_time": elapsed,
        "status": "sat",
        "sol": sol,
        "obj": None
    }


def run_external_optimization(solver_cmd, n, label, use_symmetry):
    start_global = time.time()
    low, high = 0, n - 1
    best_diff = None
    best_sol = None
    proved_optimal = True

    while low <= high:
        if time.time() - start_global >= TIME_LIMIT:
            proved_optimal = False
            break

        mid = (low + high) // 2

        smt2_path = write_smtlib_file(
            n,
            label,
            use_symmetry=use_symmetry,
            max_diff=mid
        )

        remaining = TIME_LIMIT - (time.time() - start_global)
        if remaining <= 0:
            proved_optimal = False
            break

        elapsed, out, status = call_external_solver_once(
            solver_cmd,
            smt2_path,
            remaining_time=remaining
        )

        if status == "unsat":
            low = mid + 1
            continue

        if status != "sat":
            proved_optimal = False
            break

        sol = decode_smt_model(out, n)
        if not is_full_schedule(sol):
            proved_optimal = False
            break

        best_diff = mid
        best_sol = sol
        high = mid - 1

    total = time.time() - start_global

    # ====================================
    # CORRECT UNSAT-ALL CASE
    # ====================================
    if best_sol is None and best_diff is None:
        return {
            "time": int(total),
            "actual_time": total,
            "status": "unsat",
            "sol": [],
            "obj": None
        }

    time_int = int(total)

    if (not proved_optimal) or time_int >= TIME_LIMIT:
        return {
            "time": TIME_LIMIT,
            "actual_time": total,
            "status": "timeout",
            "sol": best_sol,
            "obj": best_diff
        }

    return {
        "time": time_int,
        "actual_time": total,
        "status": "sat",
        "sol": best_sol,
        "obj": best_diff
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", type=int, default=0)
    parser.add_argument("--mode", type=str, default="all",
                        choices=["z3", "external", "all"])
    args = parser.parse_args()

    N_VALUES = [args.n] if args.n != 0 else [6, 8, 10, 12, 14, 16]

    for n in N_VALUES:
        print(f"\n===== Running n={n} =====")
        json_path = ROOT / "res" / "SMT" / f"{n}.json"

        existing = load_json(json_path)

        if args.mode == "z3":
            cleaned = {k: v for k, v in existing.items() if k.startswith("SMT_Z3")}
        elif args.mode == "external":
            cleaned = {k: v for k, v in existing.items() if k.startswith("SMT2") and "YICES" not in k}
        else:
            cleaned = existing

        save_json(json_path, cleaned)

        # Z3 Python-solvers
        if args.mode in ("z3", "all"):
            for name, cfg in Z3_MODELS.items():
                print(f"\nZ3 model: {name}")
                before = time.time()
                run_python_model(name, cfg, n)
                after = time.time()
                print(f"    → {name} finished in {after-before:.4f}s")

        # External OpenSMT-only
        if args.mode in ("external", "all"):
            for variant_name, cfg in SMTLIB_VARIANTS.items():
                print(f"\nSMT-LIB model: {variant_name}")
                print(f"  External solver: OPENSMT")

                if not cfg["opt"]:
                    smt2_path = write_smtlib_file(
                        n,
                        variant_name,
                        use_symmetry=cfg["sym"],
                        max_diff=None
                    )
                    entry = run_external_decision(
                        OPENSMT,
                        smt2_path,
                        n
                    )
                else:
                    entry = run_external_optimization(
                        OPENSMT,
                        n,
                        variant_name,
                        use_symmetry=cfg["sym"]
                    )

                print(f"    → OPENSMT finished in {entry['actual_time']:.4f}s")

                write_result_json(
                    f"{variant_name}_OPENSMT",
                    str(json_path),
                    entry["time"],
                    entry["status"],
                    entry["sol"],
                    entry["obj"]
                )

        # SUMMARY
        print("\n===== SUMMARY =====")
        data = load_json(json_path)

        for key, entry in data.items():
            time_int = entry["time"]
            if "actual_time" in entry:
                actual = entry["actual_time"]
                print(f"{key:28s} time={time_int}  ({actual:.4f}s actual)  optimal={entry['optimal']}  obj={entry['obj']}")
            else:
                print(f"{key:28s} time={time_int}  optimal={entry['optimal']}  obj={entry['obj']}")


if __name__ == "__main__":
    main()
