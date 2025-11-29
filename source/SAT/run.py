#!/usr/bin/env python3

import argparse
import subprocess
import time
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
ROOT_DIR = BASE_DIR.parent.parent
OUTPUT_DIR = ROOT_DIR / "res" / "SAT"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DIMACS_DIR = OUTPUT_DIR / "dimacs"
WCNF_DIR   = OUTPUT_DIR / "wcnf"

GLUCOSE = "glucose"
OPEN_WBO = "open-wbo"

# ----------------------------------------------------------------------
# Model registries
# ----------------------------------------------------------------------

Z3_MODELS = {
    "z3_sat"       : {"script": "sat_z3.py",        "opt": False},
    "z3_sat_sb"    : {"script": "sat_z3_sb.py",     "opt": False},
    "z3_opt"       : {"script": "sat_z3_opt.py",    "opt": True},
    "z3_opt_sb"    : {"script": "sat_z3_opt_sb.py", "opt": True},
}

CNF_MODELS = {
    "cnf"      : {"generator": "sat_dimacs.py", "sym": False},
    "cnf_sb"   : {"generator": "sat_dimacs.py", "sym": True},
}

WCNF_MODELS = {
    "maxsat"    : {"generator": "sat_wcnf.py", "sym": False},
    "maxsat_sb" : {"generator": "sat_wcnf.py", "sym": True},
}

# ----------------------------------------------------------------------
# Args
# ----------------------------------------------------------------------

parser = argparse.ArgumentParser()

parser.add_argument("-n", type=int, default=0)
parser.add_argument("--mode", type=str, default="all",
                    choices=["z3", "cnf", "maxsat", "all"])
parser.add_argument("--decision_only", action="store_true")
parser.add_argument("--opt_only", action="store_true")

args = parser.parse_args()

if args.n == 0:
    N_VALUES = [6, 8, 10, 12, 16]
else:
    N_VALUES = [args.n]

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

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

# ----------------------------------------------------------------------
# Z3 execution
# ----------------------------------------------------------------------

def run_z3_model(name, cfg, n):
    script = BASE_DIR / cfg["script"]
    json_path = OUTPUT_DIR / f"{n}.json"

    try:
        subprocess.run(
            ["python", str(script), str(n)],
            text=True,
            capture_output=True,
            timeout=300
        )
    except subprocess.TimeoutExpired:
        safe_update_json(json_path, {name: timeout_result()})
        return timeout_result()

    # After solver run, JSON should contain entry
    full = load_json(json_path)
    if name not in full:
        # solver failed / crashed / wrote nothing
        safe_update_json(json_path, {name: timeout_result()})
        return timeout_result()

    return full[name]

# ----------------------------------------------------------------------
# DIMACS generation + Glucose solving
# ----------------------------------------------------------------------

def generate_dimacs(model_cfg, n):
    gen_script = BASE_DIR / model_cfg["generator"]
    dimacs_out = DIMACS_DIR / f"{n}.cnf"

    args = ["python", str(gen_script), str(n)]
    if model_cfg.get("sym"):
        args.append("--sym")

    try:
        subprocess.run(args, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return None

    return dimacs_out

def run_glucose(path):
    try:
        subprocess.run(
            ["wsl", GLUCOSE, str(path)],
            text=True,
            capture_output=True,
            timeout=300
        )
        return True
    except subprocess.TimeoutExpired:
        return False

# ----------------------------------------------------------------------
# WCNF generation + Open-WBO solving
# ----------------------------------------------------------------------

def generate_wcnf(model_cfg, n):
    gen_script = BASE_DIR / model_cfg["generator"]
    wcnf_out = WCNF_DIR / f"{n}.wcnf"

    args = ["python", str(gen_script), str(n)]
    if model_cfg.get("sym"):
        args.append("--sym")

    try:
        subprocess.run(args, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return None

    return wcnf_out

def run_open_wbo(path):
    try:
        subprocess.run(
            ["wsl", OPEN_WBO, str(path)],
            text=True,
            capture_output=True,
            timeout=300
        )
        return True
    except subprocess.TimeoutExpired:
        return False

# ----------------------------------------------------------------------
# MAIN LOOP
# ----------------------------------------------------------------------

for n in N_VALUES:
    print(f"\n======= Running n = {n} =======")
    json_path = OUTPUT_DIR / f"{n}.json"

    # ---------- Z3 ----------
    if args.mode in ["z3", "all"]:
        for name, cfg in Z3_MODELS.items():

            if args.decision_only and cfg["opt"]:
                continue
            if args.opt_only and not cfg["opt"]:
                continue

            print(f"\nZ3 model: {name}")
            run_z3_model(name, cfg, n)

    # ---------- CNF ----------
    if args.mode in ["cnf", "all"]:
        for name, cfg in CNF_MODELS.items():

            if args.opt_only:
                continue

            print(f"\nCNF model: {name}")
            cnf_path = generate_dimacs(cfg, n)

            if cnf_path is None:
                safe_update_json(json_path, {name: timeout_result()})
                continue

            solved = run_glucose(cnf_path)

            if solved:
                safe_update_json(json_path, {
                    name: {
                        "time": 0,
                        "optimal": True,
                        "obj": None,
                        "sol": []
                    }
                })
            else:
                safe_update_json(json_path, {name: timeout_result()})

    # ---------- MAXSAT ----------
    if args.mode in ["maxsat", "all"]:
        for name, cfg in WCNF_MODELS.items():

            if args.decision_only:
                continue

            print(f"\nMaxSAT model: {name}")
            wcnf_path = generate_wcnf(cfg, n)

            if wcnf_path is None:
                safe_update_json(json_path, {name: timeout_result()})
                continue

            solved = run_open_wbo(wcnf_path)

            if solved:
                safe_update_json(json_path, {
                    name: {
                        "time": 0,
                        "optimal": True,
                        "obj": None,
                        "sol": []
                    }
                })
            else:
                safe_update_json(json_path, {name: timeout_result()})

print("\n Done.\n")
