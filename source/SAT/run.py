#!/usr/bin/env python3

import argparse
import subprocess
import json
from pathlib import Path
import time

import sat_dimacs
import sat_decode

BASE_DIR = Path(__file__).parent
ROOT_DIR = BASE_DIR.parent.parent
OUTPUT_DIR = ROOT_DIR / "res" / "SAT"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DIMACS_DIR = OUTPUT_DIR / "dimacs"

GLUCOSE = "glucose"

Z3_MODELS = {
    "z3_sat"       : {"script": "sat_z3.py",        "opt": False},
    "z3_sat_sb"    : {"script": "sat_z3_sb.py",     "opt": False},
    "z3_opt"       : {"script": "sat_z3_opt.py",    "opt": True},
    "z3_opt_sb"    : {"script": "sat_z3_opt_sb.py", "opt": True},
}

# Glucose models
GLUCOSE_MODELS = {
    "glucose"    : {"sym": False},
    "glucose_sb" : {"sym": True},
}

parser = argparse.ArgumentParser()
parser.add_argument("-n", type=int, default=0)
parser.add_argument("--mode", type=str, default="all",
                    choices=["z3", "glucose", "all"])
parser.add_argument("--decision_only", action="store_true")
parser.add_argument("--opt_only", action="store_true")
args = parser.parse_args()

if args.n == 0:
    N_VALUES = [6, 8, 10, 12, 16]
else:
    N_VALUES = [args.n]


def load_json(path: Path):
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def safe_update_json(json_path, entry):
    data = load_json(json_path)
    data.update(entry)
    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)


def timeout_result():
    return {
        "time": 300,
        "optimal": False,
        "obj": None,
        "sol": []
    }


def run_z3_model(name, cfg, n):
    script = BASE_DIR / cfg["script"]
    json_path = OUTPUT_DIR / f"{n}.json"

    try:
        subprocess.run(
            ["python3", str(script), str(n)],
            text=True,
            timeout=300
        )
    except subprocess.TimeoutExpired:
        safe_update_json(json_path, {name: timeout_result()})
        return timeout_result()

    full = load_json(json_path)
    if name not in full:
        safe_update_json(json_path, {name: timeout_result()})
        return timeout_result()

    return full[name]


def generate_dimacs(model_cfg, n):
    """
    Build DIMACS in-process using sat_dimacs, so we keep reverse_var
    for decoding, and write CNF to res/SAT/dimacs/{n}.cnf.
    Returns: (path, reverse_var_copy) or (None, None) on failure.
    """
    DIMACS_DIR.mkdir(parents=True, exist_ok=True)
    dimacs_out = DIMACS_DIR / f"{n}.cnf"

    try:
        sat_dimacs.build_dimacs(n, use_sym=model_cfg.get("sym", False))
    except Exception:
        return None, None

    try:
        with dimacs_out.open("w") as f:
            f.write(f"p cnf {sat_dimacs.next_var-1} {len(sat_dimacs.clauses)}\n")
            for clause in sat_dimacs.clauses:
                f.write(" ".join(str(l) for l in clause) + " 0\n")
    except Exception:
        return None, None

    return dimacs_out, sat_dimacs.get_reverse_map()


def run_glucose(path):
    """
    Run Glucose on given CNF path, return (status, output).
    status ∈ {"sat", "unsat", "unknown", "timeout"}.
    """
    try:
        # IMPORTANT: -model so we actually get assignments
        result = subprocess.run(
            [GLUCOSE, "-model", str(path)],
            text=True,
            capture_output=True,
            timeout=300
        )
        output = result.stdout + result.stderr
        if "s SATISFIABLE" in output:
            return "sat", output
        if "s UNSATISFIABLE" in output:
            return "unsat", output
        return "unknown", output
    except subprocess.TimeoutExpired:
        return "timeout", ""


for n in N_VALUES:
    print(f"\n======= Running n = {n} =======")
    json_path = OUTPUT_DIR / f"{n}.json"

    # Z3
    if args.mode in ["z3", "all"]:
        for name, cfg in Z3_MODELS.items():
            if args.decision_only and cfg["opt"]:
                continue
            if args.opt_only and not cfg["opt"]:
                continue
            print(f"\nZ3 model: {name}")
            run_z3_model(name, cfg, n)

    # Glucose 
    if args.mode in ["glucose", "all"]:
        for name, cfg in GLUCOSE_MODELS.items():
            if args.opt_only:
                continue

            print(f"\nGlucose model: {name}")

            start_all = time.time()

            cnf_path, reverse_map = generate_dimacs(cfg, n)

            if cnf_path is None:
                safe_update_json(json_path, {name: timeout_result()})
                print(f"[{name}] n={n} timeout (DIMACS generation)")
                continue

            status, output = run_glucose(cnf_path)
            elapsed = time.time() - start_all

            if status == "sat":
                print(f"[{name}] n={n} sat time={elapsed:.3f}s, decoding...")

                assignments = sat_decode.parse_glucose_solution(output)
                sol = sat_decode.decode_schedule(assignments, reverse_map, n)

                if sol is None:
                    # SAT but we failed to reconstruct a full schedule we treat as timeout/failed approach
                    print(f"[{name}] decoding failed → marking as timeout_result")
                    safe_update_json(json_path, {name: timeout_result()})
                    continue

                # Valid schedule
                safe_update_json(json_path, {
                    name: {
                        "time": int(min(elapsed, 300)),
                        "optimal": True,
                        "obj": None,
                        "sol": sol
                    }
                })

            elif status == "unsat":
                print(f"[{name}] n={n} unsat time={elapsed:.3f}s")
                safe_update_json(json_path, {
                    name: {
                        "time": int(min(elapsed, 300)),
                        "optimal": True,
                        "obj": None,
                        "sol": []
                    }
                })

            else:
                # unknown or timeout
                print(f"[{name}] n={n} timeout/unknown → time=300s, optimal=false")
                safe_update_json(json_path, {name: timeout_result()})

print("\nDone.\n")
