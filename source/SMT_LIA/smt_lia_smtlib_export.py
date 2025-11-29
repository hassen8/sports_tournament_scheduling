# source/SMT_LIA/smt_lia_smtlib_export.py
#
# Export LIA model as SMT-LIB2 with:
#   (set-option :produce-models true)
#   (set-logic QF_LIA)
#   ...
#   (get-model)

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "source"))
sys.path.append(str(ROOT / "source" / "SMT_LIA"))

from smt_lia_core import build_smt_lia_model


def write_smtlib_file(n, variant_name, use_symmetry=False, max_diff=None):
    """
    Build the LIA model and export to an SMT-LIB2 file in res2/SMT_LIA/smt2.

    variant_name is used only for naming; logic is always QF_LIA.
    """
    s, H, Weeks, Periods = build_smt_lia_model(
        n,
        use_symmetry=use_symmetry,
        max_diff=max_diff
    )

    out_dir = ROOT / "res2" / "SMT_LIA" / "smt2"
    out_dir.mkdir(parents=True, exist_ok=True)

    if use_symmetry and max_diff is not None:
        suffix = "_opt_sb"
    elif use_symmetry:
        suffix = "_sb"
    elif max_diff is not None:
        suffix = "_opt"
    else:
        suffix = ""

    out_path = out_dir / f"{n}{suffix}.smt2"

    with open(out_path, "w") as f:
        f.write("(set-option :produce-models true)\n")
        f.write("(set-logic QF_LIA)\n\n")
        f.write(s.to_smt2())
        f.write("\n(get-model)\n")

    print(f"[SMT_LIA_LIB] SMT-LIB written to {out_path}")
    return out_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("n", type=int)
    parser.add_argument("--sym", action="store_true")
    parser.add_argument("--opt", action="store_true")
    args = parser.parse_args()

    n = args.n
    sym = args.sym
    opt = args.opt

    max_diff = 0 if opt else None
    write_smtlib_file(n, "CLI", use_symmetry=sym, max_diff=max_diff)
