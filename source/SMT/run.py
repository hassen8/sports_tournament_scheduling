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

# ------------------------------------------------------------
# External solver commands
# ------------------------------------------------------------
Z3_CLI   = "z3"
CVC5     = "cvc5"
YICES    = "yices-smt2"
OPENSMT  = "opensmt"

# ------------------------------------------------------------
# Python-based Z3 solvers
# ------------------------------------------------------------
Z3_MODELS = {
    "SMT_Z3":        {"script": "smt_z3.py"},
    "SMT_Z3_SB":     {"script": "smt_z3_sb.py"},
    "SMT_Z3_OPT":    {"script": "smt_z3_opt.py"},
    "SMT_Z3_OPT_SB": {"script": "smt_z3_opt_sb.py"},
}

# ------------------------------------------------------------
# SMT-LIB variants
# ------------------------------------------------------------
SMTLIB_VARIANTS = {
    "SMT2":          {"sym": False, "opt": False},
    "SMT2_SB":       {"sym": True,  "opt": False},
    "SMT2_OPT":      {"sym": False, "opt": True},
    "SMT2_OPT_SB":   {"sym": True,  "opt": True},
}

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
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


# ------------------------------------------------------------
# Run Python Z3 model
# ------------------------------------------------------------
def run_python_model(name, cfg, n):
    script = ROOT / "source" / "SMT" / cfg["script"]
    try:
        subprocess.run(
            [sys.executable, str(script), str(n)],
            capture_output=True,
            text=True,
            timeout=300
        )
    except subprocess.TimeoutExpired:
        return None

    json_path = ROOT / "res" / "SMT" / f"{n}.json"
    return load_json(json_path)


# ------------------------------------------------------------
# External solver execution
# ------------------------------------------------------------
def run_external_solver(variant_label, solver_cmd, smt2_path, n):
    try:
        start = time.time()
        proc = subprocess.run(
            [solver_cmd, str(smt2_path)],
            capture_output=True,
            text=True,
            timeout=300
        )
        elapsed = time.time() - start
    except subprocess.TimeoutExpired:
        return {"time": 300, "optimal": False, "obj": None, "sol": []}

    output = proc.stdout.lower()

    if "unsat" in output:
        return {"time": int(elapsed), "optimal": True, "obj": None, "sol": []}

    if "sat" not in output:
        return {"time": 300, "optimal": False, "obj": None, "sol": []}

    sol = decode_smt_model(proc.stdout, n)
    empty = all(all(x is None for x in row) for row in sol)

    return {
        "time": int(min(elapsed, 300)),
        "optimal": not empty,
        "obj": None,
        "sol": sol
    }


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", type=int, default=0)
    parser.add_argument("--mode", type=str, default="all",
                        choices=["z3", "external", "all"])
    args = parser.parse_args()

    N_VALUES = [args.n] if args.n != 0 else [6, 8, 10, 12, 14, 16, 18, 20]

    for n in N_VALUES:
        print(f"\n===== Running n={n} =====")
        json_path = ROOT / "res" / "SMT" / f"{n}.json"

        # Load old JSON (if any)
        existing = load_json(json_path)

        # ----------------------------------------------------
        # CLEANUP LOGIC
        # ----------------------------------------------------
        cleaned = {}

        if args.mode == "z3":
            # Keep only SMT_Z3-* entries
            for key, val in existing.items():
                if key.startswith("SMT_Z3"):
                    cleaned[key] = val

        elif args.mode == "external":
            # Keep only SMT2-* entries
            for key, val in existing.items():
                if key.startswith("SMT2"):
                    cleaned[key] = val

        else:  # mode == "all"
            # Keep everything
            cleaned = existing.copy()

        save_json(json_path, cleaned)

        # ----------------------------------------------------
        # 1) Run Python Z3 solvers
        # ----------------------------------------------------
        if args.mode in ("z3", "all"):
            for name, cfg in Z3_MODELS.items():
                print(f"\nZ3 model: {name}")
                run_python_model(name, cfg, n)

        # ----------------------------------------------------
        # 2) Run external SMT solvers
        # ----------------------------------------------------
        if args.mode in ("external", "all"):
            for variant_name, cfg in SMTLIB_VARIANTS.items():
                print(f"\nSMT-LIB model: {variant_name}")

                smt2_path = write_smtlib_file(
                    n,
                    variant_name,
                    use_symmetry=cfg["sym"],
                    max_diff=(0 if cfg["opt"] else None)
                )

                for solver_label, solver_bin in [
                    ("CVC5", CVC5),
                    ("Z3_CLI", Z3_CLI),
                    ("YICES", YICES),
                    ("OPENSMT", OPENSMT)
                ]:
                    print(f"  External solver: {solver_label}")

                    entry = run_external_solver(
                        f"{variant_name}_{solver_label}",
                        solver_bin,
                        smt2_path,
                        n
                    )

                    write_result_json(
                        f"{variant_name}_{solver_label}",
                        n,
                        json_path,
                        entry["time"],
                        entry["optimal"],
                        entry["sol"],
                        entry["obj"]
                    )

        # ----------------------------------------------------
        # Summary
        # ----------------------------------------------------
        print("\n===== SUMMARY =====")
        data = load_json(json_path)
        for key, entry in data.items():
            print(f"{key:25s} time={entry['time']} optimal={entry['optimal']} obj={entry['obj']}")


if __name__ == "__main__":
    main()
