# source/SMT/smtlib_export.py
#
# Unified SMT-LIB exporter for STS
# Provides write_smtlib_file() for run_smt.py
# Also supports standalone CLI usage.

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "source"))

from SMT.smt_core import build_smt_model


def write_smtlib(solver, path):
    """
    Write solver to SMT-LIB with:
    - model production enabled
    - explicit logic
    - (get-model) appended so external solvers print assignments
    """
    with open(path, "w") as f:
        f.write("(set-option :produce-models true)\n")
        f.write("(set-logic QF_UF)\n\n")
        f.write(solver.to_smt2())
        f.write("\n(get-model)\n")


def write_smtlib_file(n, variant_name, use_symmetry, max_diff):
    """
    Build STS model and write SMT-LIB file.
    Called from run_smt.py.

    Args:
        n : number of teams
        variant_name : "SMT2", "SMT2_SB", "SMT2_OPT", "SMT2_OPT_SB"
        use_symmetry : bool
        max_diff : None (decision), or 0 (optimization but no search)
    """
    solver, H, Weeks, Periods = build_smt_model(
        n,
        use_symmetry=use_symmetry,
        max_diff=max_diff,
    )

    out_dir = ROOT / "res" / "SMT" / "smt2"
    out_dir.mkdir(parents=True, exist_ok=True)

    # filename pattern used by run_smt summary
    name_lower = variant_name.lower()
    out_path = out_dir / f"{name_lower}_{n}.smt2"

    write_smtlib(solver, out_path)
    return out_path


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("n", type=int)
    parser.add_argument("--sym", action="store_true")
    parser.add_argument("--opt", action="store_true")
    args = parser.parse_args()

    n = args.n
    sym = args.sym
    opt = args.opt

    solver, H, Weeks, Periods = build_smt_model(
        n,
        use_symmetry=sym,
        max_diff=(0 if opt else None)
    )

    out_dir = ROOT / "res" / "SMT" / "smt2"
    out_dir.mkdir(parents=True, exist_ok=True)

    if sym and opt:
        out_path = out_dir / f"{n}_opt_sb.smt2"
    elif sym:
        out_path = out_dir / f"{n}_sb.smt2"
    elif opt:
        out_path = out_dir / f"{n}_opt.smt2"
    else:
        out_path = out_dir / f"{n}.smt2"

    write_smtlib(solver, out_path)
    print(f"[SMT_LIB] SMT-LIB written to {out_path}")


if __name__ == "__main__":
    main()
