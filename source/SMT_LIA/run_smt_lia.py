# source/SMT_LIA/run_smt_lia.py
#
# Main driver for QF-LIA SMT experiments on STS.
# - Runs Python Z3 LIA models
# - Runs external solvers on SMT-LIB QF_LIA exports
# - Writes results to res2/SMT_LIA/<n>.json
#
# Approaches:
#   SMT_LIA_Z3
#   SMT_LIA_Z3_SB
#   SMT_LIA_Z3_OPT
#   SMT_LIA_Z3_OPT_SB
#   SMT2_LIA_*_<SOLVER>

import sys
import subprocess
import time
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "source"))
sys.path.append(str(ROOT / "source" / "SMT_LIA"))

from common.io_json import write_result_json
from smt_lia_decode import decode_smt_lia_model
from smt_lia_smtlib_export import write_smtlib_file

# External solver binaries (assumed in PATH under WSL)
Z3_CLI  = "z3"
CVC5    = "cvc5"
YICES   = "yices-smt2"
OPENSMT = "opensmt"


LIA_Z3_MODELS = {
    "SMT_LIA_Z3":        {"script": "smt_lia_z3.py"},
    "SMT_LIA_Z3_SB":     {"script": "smt_lia_z3_sb.py"},
    "SMT_LIA_Z3_OPT":    {"script": "smt_lia_z3_opt.py"},
    "SMT_LIA_Z3_OPT_SB": {"script": "smt_lia_z3_opt_sb.py"},
}

SMTLIB_VARIANTS = {
    "SMT2_LIA":        {"sym": False, "opt": False},
    "SMT2_LIA_SB":     {"sym": True,  "opt": False},
    "SMT2_LIA_OPT":    {"sym": False, "opt": True},
    "SMT2_LIA_OPT_SB": {"sym": True,  "opt": True},
}


def load_json(path: Path):
    if not path.exists():
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def run_python_model(name, cfg, n):
    script = ROOT / "source" / "SMT_LIA" / cfg["script"]

    try:
        start = time.time()
        subprocess.run(
            [sys.executable, str(script), str(n)],
            capture_output=True,
            text=True,
            timeout=320
        )
        elapsed = time.time() - start
    except subprocess.TimeoutExpired:
        print(f"  [WARN] Python model {name} timed out.")
        elapsed = 320.0

    json_path = ROOT / "res2" / "SMT_LIA" / f"{n}.json"
    data = load_json(json_path)
    if not data:
        print(f"  [WARN] No JSON data written by {name}.")
    return data, elapsed


def run_external_solver(variant_name, solver_label, solver_bin, smt2_path, n, json_path):
    """Run one external solver; return entry dict."""
    try:
        start = time.time()
        proc = subprocess.run(
            [solver_bin, str(smt2_path)],
            capture_output=True,
            text=True,
            timeout=320
        )
        elapsed = time.time() - start
    except subprocess.TimeoutExpired:
        elapsed = 320.0
        write_result_json(
            f"{variant_name}_{solver_label}",
            n,
            json_path,
            300,
            False,
            [],
            obj=None,
        )
        print(f"  [{variant_name}_{solver_label}] Timeout")
        return

    out = proc.stdout
    lower = out.lower()
    err = proc.stderr

    if err.strip():
        # Just print errors to help debugging, but still continue
        print(err)

    is_sat = ("sat" in lower) and ("unsat" not in lower)

    if not is_sat:
        # UNSAT or unknown: no solution
        time_capped = int(300 if elapsed > 300 else elapsed)
        write_result_json(
            f"{variant_name}_{solver_label}",
            n,
            json_path,
            time_capped,
            False,
            [],
            obj=None,
        )
        print(f"  [{variant_name}_{solver_label}] UNSAT/UNKNOWN")
        return

    # SAT: decode model
    sol = decode_smt_lia_model(out, n)

    # Require a fully filled schedule; otherwise treat as invalid
    periods = n // 2
    weeks = n - 1
    fully_filled = True
    if len(sol) != periods:
        fully_filled = False
    else:
        for row in sol:
            if len(row) != weeks:
                fully_filled = False
                break
            if any(cell is None for cell in row):
                fully_filled = False
                break

    time_capped = int(300 if elapsed > 300 else elapsed)

    if not fully_filled:
        write_result_json(
            f"{variant_name}_{solver_label}",
            n,
            json_path,
            time_capped,
            False,
            [],
            obj=None,
        )
        print(f"  [{variant_name}_{solver_label}] SAT but invalid/partial model -> discarded")
        return

    write_result_json(
        f"{variant_name}_{solver_label}",
        n,
        json_path,
        time_capped,
        True,
        sol,
        obj=None,
    )
    print(f"  [{variant_name}_{solver_label}] SAT, schedule decoded, time={time_capped}s")


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-n", type=int, default=0)
    parser.add_argument(
        "--mode",
        type=str,
        default="all",
        choices=["z3", "external", "all"],
    )
    args = parser.parse_args()

    if args.n == 0:
        N_VALUES = [6, 8, 10, 12, 14, 16, 18, 20]
    else:
        N_VALUES = [args.n]

    for n in N_VALUES:
        print(f"\n===== LIA RUN n={n} =====")

        json_path = ROOT / "res2" / "SMT_LIA" / f"{n}.json"

        # Clean previous JSON so summary isn't polluted by old runs
        if json_path.exists():
            json_path.unlink()

        # 1) Python Z3 LIA models
        if args.mode in ("z3", "all"):
            for name, cfg in LIA_Z3_MODELS.items():
                print(f"\nZ3 LIA model: {name}")
                run_python_model(name, cfg, n)

        # 2) External solvers
        if args.mode in ("external", "all"):
            for variant_name, cfg in SMTLIB_VARIANTS.items():
                print(f"\nSMT-LIB LIA model: {variant_name}")
                max_diff = 0 if cfg["opt"] else None
                smt2_path = write_smtlib_file(
                    n,
                    variant_name,
                    use_symmetry=cfg["sym"],
                    max_diff=max_diff,
                )

                for solver_label, solver_bin in [
                    ("CVC5", CVC5),
                    ("Z3_CLI", Z3_CLI),
                    ("YICES", YICES),
                    ("OPENSMT", OPENSMT),
                ]:
                    print(f"  External solver: {solver_label}")
                    run_external_solver(
                        variant_name,
                        solver_label,
                        solver_bin,
                        smt2_path,
                        n,
                        json_path,
                    )

        # 3) Summary
        print("\n===== LIA SUMMARY =====\n")
        data = load_json(json_path)
        if not data:
            print("{}")
        else:
            for key in sorted(data.keys()):
                entry = data[key]
                print(f"{key:25s} time={entry['time']} optimal={entry['optimal']} obj={entry['obj']}")


if __name__ == "__main__":
    main()
