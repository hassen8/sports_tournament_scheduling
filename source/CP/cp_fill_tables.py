#!/usr/bin/env python3
import json
import argparse
from pathlib import Path

DECISION = [
    ("Chuffed",    "chuffed_reg"),
    ("Chuffed+SB", "chuffed_sb"),
    ("CP-SAT",     "cp_reg"),
    ("CP-SAT+SB",  "cp_sb"),
    ("Gecode",     "gecode_reg"),
    ("Gecode+SB",  "gecode_sb"),
]

OPT = [
    ("Chuffed",    "chuffed_opt_reg"),
    ("Chuffed+SB", "chuffed_opt_sb"),
    ("CP-SAT",     "cp_opt_reg"),
    ("CP-SAT+SB",  "cp_opt_sb"),
    ("Gecode",     "gecode_opt_reg"),
    ("Gecode+SB",  "gecode_opt_sb"),
]

DECISION_SS = [
    ("Chuffed+SS",    "chuffed_reg_ss"),
    ("Chuffed+SB+SS", "chuffed_sb_ss"),
    ("CP-SAT+SS",     "cp_reg_ss"),
    ("CP-SAT+SB+SS",  "cp_sb_ss"),
    ("Gecode+SS",     "gecode_reg_ss"),
    ("Gecode+SB+SS",  "gecode_sb_ss"),
]

OPT_SS = [
    ("Chuffed+SS",    "chuffed_opt_reg_ss"),
    ("Chuffed+SB+SS", "chuffed_opt_sb_ss"),
    ("CP-SAT+SS",     "cp_opt_reg_ss"),
    ("CP-SAT+SB+SS",  "cp_opt_sb_ss"),
    ("Gecode+SS",     "gecode_opt_reg_ss"),
    ("Gecode+SB+SS",  "gecode_opt_sb_ss"),
]


def find_res_cp(start: Path) -> Path | None:
    """Walk up from start looking for res/CP."""
    for p in [start] + list(start.parents):
        cand = p / "res" / "CP"
        if cand.exists() and cand.is_dir():
            return cand
    return None


def load_json(p: Path) -> dict:
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def decision_cell(d: dict, key: str) -> str:
    p = d.get(key)
    if not isinstance(p, dict):
        return "NA"
    if p.get("optimal") is True and isinstance(p.get("time"), (int, float)):
        return str(int(p["time"]))
    return "NA"


def opt_cell(d: dict, key: str) -> str:
    p = d.get(key)
    if not isinstance(p, dict):
        return "NA"
    obj = p.get("obj", None)
    sol = p.get("sol", [])
    if obj is None or not isinstance(sol, list) or len(sol) == 0:
        return "NA"
    s = str(int(obj)) if isinstance(obj, (int, float)) else str(obj)
    return (r"\textbf{" + s + "}") if p.get("optimal") is True else s


def render_table(ns, cols, caption, label, mode, base_dir: Path) -> str:
    headers = [h for (h, _) in cols]
    keys = [k for (_, k) in cols]
    colspec = "l@{\\extracolsep{\\fill}}" + ("c" * len(keys))

    lines = []
    lines += [
        r"\begin{table}[H]",
        r"\centering",
        rf"\begin{{tabularx}}{{\textwidth}}{{{colspec}}}",
        r"\toprule",
        "N & " + " & ".join(headers) + r" \\",
        r"\midrule",
    ]

    missing_files = 0

    for n in ns:
        fp = base_dir / f"{n}.json"
        if not fp.exists():
            missing_files += 1
            d = {}
        else:
            d = load_json(fp)

        cells = []
        for k in keys:
            cells.append(decision_cell(d, k) if mode == "decision" else opt_cell(d, k))

        lines.append(f"{n}  & " + " & ".join(cells) + r" \\")

    lines += [
        r"\bottomrule",
        r"\end{tabularx}",
        r"\caption{" + caption + r"}",
        r"\label{" + label + r"}",
        r"\end{table}",
    ]

    # Loud warning if the directory is wrong
    if missing_files == len(ns):
        lines.insert(0, f"% WARNING: No JSON files found in: {base_dir}")
    elif missing_files > 0:
        lines.insert(0, f"% WARNING: Missing {missing_files}/{len(ns)} JSON files in: {base_dir}")

    return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=str, default="", help="Path to res/CP (optional). If omitted, auto-detects.")
    ap.add_argument("--ns", type=str, default="6,8,10,12,14,16,18,20,22", help="comma-separated N list")
    args = ap.parse_args()

    ns = [int(x.strip()) for x in args.ns.split(",") if x.strip()]

    script_dir = Path(__file__).resolve().parent
    base_dir = Path(args.dir).resolve() if args.dir.strip() else (find_res_cp(script_dir) or find_res_cp(Path.cwd()))

    if base_dir is None:
        raise SystemExit("ERROR: Could not auto-find res/CP. Run with --dir /full/path/to/res/CP")

    # Also print one clear debug line to stderr-like LaTeX comment
    print(f"% Using JSON directory: {base_dir}")

    print(render_table(ns, DECISION,
                       "Decision variant: runtime in seconds without custom search.",
                       "tab:cp_decision",
                       "decision", base_dir))
    print()
    print(render_table(ns, OPT,
                       "Optimization variant: best objective value (bold = proven optimal).",
                       "tab:cp_opt",
                       "opt", base_dir))
    print()
    print(render_table(ns, DECISION_SS,
                       "Decision variant: runtime in seconds with custom search.",
                       "tab:cp_decision_ss",
                       "decision", base_dir))
    print()
    print(render_table(ns, OPT_SS,
                       "Optimization variant with custom search: best objective value.",
                       "tab:cp_opt_ss",
                       "opt", base_dir))
