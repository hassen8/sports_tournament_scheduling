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

# External solvers
YICES   = "yices-smt2"
OPENSMT = "opensmt"

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


def run_external_solver(solver_cmd, smt2_path, n):
    try:
        start = time.time()
        proc = subprocess.run(
            [solver_cmd, str(smt2_path)],
            text=True,
            capture_output=True,
            timeout=300
        )
        elapsed = time.time() - start
    except subprocess.TimeoutExpired:
        return {
            "time": 300,
            "actual_time": 300.0,
            "status": "timeout",
            "sol": [],
            "obj": None
        }

    output = proc.stdout.lower()

    # UNSAT case
    if "unsat" in output:
        return {
            "time": int(elapsed),
            "actual_time": elapsed,
            "status": "unsat",
            "sol": [],
            "obj": None
        }

    # No SAT → treated as timeout/unknown
    if "sat" not in output:
        return {
            "time": 300,
            "actual_time": elapsed,
            "status": "timeout",
            "sol": [],
            "obj": None
        }

    # SAT → attempt decoding
    sol = decode_smt_model(proc.stdout, n)
    empty = all(all(x is None for x in row) for row in sol)

    return {
        "time": int(min(elapsed, 300)),
        "actual_time": elapsed,
        "status": "sat" if not empty else "timeout",
        "sol": sol if not empty else [],
        "obj": None
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
            cleaned = {k: v for k, v in existing.items() if k.startswith("SMT2")}
        else:
            cleaned = existing

        save_json(json_path, cleaned)

        if args.mode in ("z3", "all"):
            for name, cfg in Z3_MODELS.items():
                print(f"\nZ3 model: {name}")
                before = time.time()
                run_python_model(name, cfg, n)
                after = time.time()
                print(f"    → {name} finished in {after-before:.4f}s")

        if args.mode in ("external", "all"):
            for variant_name, cfg in SMTLIB_VARIANTS.items():
                print(f"\nSMT-LIB model: {variant_name}")

                smt2_path = write_smtlib_file(
                    n,
                    variant_name,
                    use_symmetry=cfg["sym"],
                    max_diff=(0 if cfg["opt"] else None)
                )

                for solver_label, solver_cmd in [
                    ("YICES", YICES),
                    ("OPENSMT", OPENSMT)
                ]:
                    print(f"  External solver: {solver_label}")
                    entry = run_external_solver(
                        solver_cmd,
                        smt2_path,
                        n
                    )

                    print(f"    → {solver_label} finished in {entry['actual_time']:.4f}s")

                    write_result_json(
                        f"{variant_name}_{solver_label}",
                        str(json_path),
                        entry["time"],
                        entry["status"],
                        entry["sol"],
                        entry["obj"]
                    )

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
