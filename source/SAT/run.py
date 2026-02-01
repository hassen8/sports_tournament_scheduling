#!/usr/bin/env python3
"""
Run SAT approach (Glucose) for STS.
"""

import argparse
import subprocess
import json
import time
from pathlib import Path

import sat_dimacs
import sat_decode

GLUCOSE = "glucose"
TIMEOUT = 300

BASE_DIR = Path(__file__).parent
ROOT_DIR = BASE_DIR.parent.parent
OUTPUT_DIR = ROOT_DIR / "res" / "SAT"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DIMACS_DIR = OUTPUT_DIR / "dimacs"
DIMACS_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except:
        return {}


def safe_update_json(json_path: Path, entry: dict):
    data = load_json(json_path)
    data.update(entry)
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def timeout_result():
    return {"time": 300, "optimal": False, "obj": None, "sol": []}


def run_glucose(cnf_path: Path):
    """
    Run Glucose on given CNF file.
    Return (status, output):
      status in {"sat","unsat","unknown","timeout"}
    """
    try:
        r = subprocess.run(
            [GLUCOSE, "-model", str(cnf_path)],
            text=True,
            capture_output=True,
            timeout=TIMEOUT
        )
        out = r.stdout + r.stderr
        if "s SATISFIABLE" in out:
            return "sat", out
        if "s UNSATISFIABLE" in out:
            return "unsat", out
        return "unknown", out
    except subprocess.TimeoutExpired:
        return "timeout", ""


def generate_dimacs(n: int, use_sym: bool):
    """
    Generate CNF in-process so we can keep the reverse map for decoding.
    Writes: res/SAT/dimacs/{n}.cnf
    Returns (cnf_path, reverse_map, pairings)
    """
    sat_dimacs.build_dimacs(n, use_sym=use_sym, anchor_week=args.anchor_week)
    #print(f"n={n} vars={sat_dimacs.next_var-1} clauses={len(sat_dimacs.clauses)} sym={args.sym}")

    cnf_path = DIMACS_DIR / f"{n}.cnf"
    sat_dimacs.write_dimacs(str(cnf_path))

    reverse_map = sat_dimacs.get_reverse_map()
    pairings = sat_dimacs.get_pairings()
    return cnf_path, reverse_map, pairings


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", type=int, default=0)
    parser.add_argument("--sym", action="store_true", help="enable symmetry breaking")
    parser.add_argument("--anchor_week", type=int, default=0)
    parser.add_argument("--all", action="store_true", help="run both glucose and glucose_sb for all n")
    args = parser.parse_args()

    if args.all or args.n == 0:
        N_VALUES = [6, 8, 10, 12, 14, 16, 18, 20, 22]
    else:
        N_VALUES = [args.n]

    for n in N_VALUES:
        print(f"\n====== Running n = {n} ======")
        json_path = OUTPUT_DIR / f"{n}.json"

        sym_values = [args.sym]
        if args.all:
            sym_values = [False, True]

        for sym in sym_values:
            approach = "glucose_sb" if sym else "glucose"

            start_all = time.time()

            try:
                cnf_path, reverse_map, pairings = generate_dimacs(n, use_sym=sym)
            except Exception as e:
                print(f"[{approach}] CNF generation failed: {e}")
                safe_update_json(json_path, {approach: timeout_result()})
                continue

            status, output = run_glucose(cnf_path)

            elapsed = time.time() - start_all

            if status == "sat":
                print(f"[{approach}] n={n} SAT time={elapsed:.3f}s, decoding...")

                assignments = sat_decode.parse_glucose_solution(output)
                sol = sat_decode.decode_schedule(assignments, reverse_map, pairings, n)

                if sol is None:
                    print(f"[{approach}] decoding failed -> marking as timeout")
                    safe_update_json(json_path, {approach: timeout_result()})
                    continue

                safe_update_json(json_path, {
                    approach: {
                        "time": int(min(elapsed, TIMEOUT)),
                        "optimal": True,
                        "obj": None,
                        "sol": sol
                    }
                })

            elif status == "unsat":
                print(f"[{approach}] n={n} UNSAT time={elapsed:.3f}s")
                safe_update_json(json_path, {
                    approach: {
                        "time": int(min(elapsed, TIMEOUT)),
                        "optimal": True,
                        "obj": None,
                        "sol": []
                    }
                })

            else:
                print(f"[{approach}] n={n} TIMEOUT/UNKNOWN -> marking time=300")
                safe_update_json(json_path, {approach: timeout_result()})


    print("\nDone.\n")
