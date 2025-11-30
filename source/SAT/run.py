#!/usr/bin/env python3

import argparse
import subprocess
import json
from pathlib import Path
import time

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

# Renamed CNF models → Glucose models
GLUCOSE_MODELS = {
    "glucose"    : {"generator": "sat_dimacs.py", "sym": False},
    "glucose_sb" : {"generator": "sat_dimacs.py", "sym": True},
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
    gen_script = BASE_DIR / model_cfg["generator"]
    DIMACS_DIR.mkdir(parents=True, exist_ok=True)
    dimacs_out = DIMACS_DIR / f"{n}.cnf"

    args = ["python3", str(gen_script), str(n)]
    if model_cfg.get("sym"):
        args.append("--sym")

    try:
        subprocess.run(args, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return None

    return dimacs_out if dimacs_out.exists() else None


def run_glucose(path):
    try:
        result = subprocess.run(
            [GLUCOSE, str(path)],
            text=True,
            capture_output=True,
            timeout=300
        )
        output = result.stdout + result.stderr
        if "s SATISFIABLE" in output:
            return "sat"
        if "s UNSATISFIABLE" in output:
            return "unsat"
        return "unknown"
    except subprocess.TimeoutExpired:
        return "timeout"


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

    # Glucose (former CNF)
    if args.mode in ["glucose", "all"]:
        for name, cfg in GLUCOSE_MODELS.items():
            if args.opt_only:
                continue

            print(f"\nGlucose model: {name}")

            start_all = time.time()

            cnf_path = generate_dimacs(cfg, n)

            if cnf_path is None:
                safe_update_json(json_path, {
                    name: {
                        "time": 300,
                        "optimal": False,
                        "obj": None,
                        "sol": []
                    }
                })
                print(f"[{name}] n={n} timeout (DIMACS generation)")
                continue

            status = run_glucose(cnf_path)
            elapsed = time.time() - start_all

            if status == "sat":
                print(f"[{name}] n={n} sat time={elapsed:.3f}s")
                safe_update_json(json_path, {
                    name: {
                        "time": int(min(elapsed, 300)),
                        "optimal": True,
                        "obj": None,
                        "sol": []
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
                print(f"[{name}] n={n} timeout time=300s")
                safe_update_json(json_path, {
                    name: {
                        "time": 300,
                        "optimal": False,
                        "obj": None,
                        "sol": []
                    }
                })

print("\nDone.\n")
