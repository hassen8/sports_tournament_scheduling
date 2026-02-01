#!/usr/bin/env python3
import json
import argparse
import contextlib
import io
from pathlib import Path
from datetime import timedelta
import time

import minizinc

from round_robin import circle_method_pairs

TIME_LIMIT = 300

parser = argparse.ArgumentParser()
parser.add_argument("-n", type=int, help="select the number of teams", default=0)

parser.add_argument("--solver", action="append", choices=["gecode", "chuffed", "cp"],
                    help="restrict to solver(s); can be repeated, e.g. --solver gecode --solver chuffed")
parser.add_argument("--decision", action="store_true", help="run decision models only")
parser.add_argument("--opt", action="store_true", help="run optimization models only")
parser.add_argument("--sb", type=int, choices=[0, 1], default=None,
                    help="restrict to symmetry breaking off/on (0/1)")
parser.add_argument("--ss", type=int, choices=[0, 1], default=None,
                    help="restrict to search strategy off/on (0/1)")
parser.add_argument("--models", type=str, default="",
                    help="comma-separated exact model keys to run (override other filters)")

args = parser.parse_args()

BASE_DIR = Path(__file__).resolve().parent
ROOT = BASE_DIR.parent.parent 
OUTPUT_DIR = ROOT / "res" / "CP"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Default N list
ALL_N = [6, 8, 10, 12, 14, 16, 18, 20]
N_VALUES = ALL_N if args.n == 0 else [int(args.n)]

MODEL_NAMES = {
    # Decision
    "gecode_reg":     {"model": f"{BASE_DIR}/cp_rr_decision.mzn", "solver": "gecode", "opt": False, "use_ss": [0, 0], "use_sb": 0},
    "gecode_sb":      {"model": f"{BASE_DIR}/cp_rr_decision.mzn", "solver": "gecode", "opt": False, "use_ss": [0, 0], "use_sb": 1},
    "chuffed_reg":    {"model": f"{BASE_DIR}/cp_rr_decision.mzn", "solver": "chuffed", "opt": False, "use_ss": [0, 0], "use_sb": 0},
    "chuffed_sb":     {"model": f"{BASE_DIR}/cp_rr_decision.mzn", "solver": "chuffed", "opt": False, "use_ss": [0, 0], "use_sb": 1},
    "cp_reg":         {"model": f"{BASE_DIR}/cp_rr_decision.mzn", "solver": "cp",     "opt": False, "use_ss": [0, 0], "use_sb": 0},
    "cp_sb":          {"model": f"{BASE_DIR}/cp_rr_decision.mzn", "solver": "cp",     "opt": False, "use_ss": [0, 0], "use_sb": 1},

    # Optimization
    "gecode_opt_reg": {"model": f"{BASE_DIR}/cp_rr_opt.mzn",      "solver": "gecode", "opt": True,  "use_ss": [0, 0], "use_sb": 0},
    "gecode_opt_sb":  {"model": f"{BASE_DIR}/cp_rr_opt.mzn",      "solver": "gecode", "opt": True,  "use_ss": [0, 0], "use_sb": 1},
    "chuffed_opt_reg":{"model": f"{BASE_DIR}/cp_rr_opt.mzn",      "solver": "chuffed","opt": True,  "use_ss": [0, 0], "use_sb": 0},
    "chuffed_opt_sb": {"model": f"{BASE_DIR}/cp_rr_opt.mzn",      "solver": "chuffed","opt": True,  "use_ss": [0, 0], "use_sb": 1},
    "cp_opt_reg":     {"model": f"{BASE_DIR}/cp_rr_opt.mzn",      "solver": "cp",     "opt": True,  "use_ss": [0, 0], "use_sb": 0},
    "cp_opt_sb":      {"model": f"{BASE_DIR}/cp_rr_opt.mzn",      "solver": "cp",     "opt": True,  "use_ss": [0, 0], "use_sb": 1},

    # Decision + Search Strategy
    "gecode_reg_ss":  {"model": f"{BASE_DIR}/cp_rr_decision.mzn", "solver": "gecode", "opt": False, "use_ss": [1, 0], "use_sb": 0},
    "gecode_sb_ss":   {"model": f"{BASE_DIR}/cp_rr_decision.mzn", "solver": "gecode", "opt": False, "use_ss": [1, 0], "use_sb": 1},
    "chuffed_reg_ss": {"model": f"{BASE_DIR}/cp_rr_decision.mzn", "solver": "chuffed","opt": False, "use_ss": [1, 0], "use_sb": 0},
    "chuffed_sb_ss":  {"model": f"{BASE_DIR}/cp_rr_decision.mzn", "solver": "chuffed","opt": False, "use_ss": [1, 0], "use_sb": 1},
    "cp_reg_ss":      {"model": f"{BASE_DIR}/cp_rr_decision.mzn", "solver": "cp",     "opt": False, "use_ss": [1, 0], "use_sb": 0},
    "cp_sb_ss":       {"model": f"{BASE_DIR}/cp_rr_decision.mzn", "solver": "cp",     "opt": False, "use_ss": [1, 0], "use_sb": 1},

    # Optimization + Search Strategy
    "gecode_opt_reg_ss": {"model": f"{BASE_DIR}/cp_rr_opt.mzn",   "solver": "gecode", "opt": True,  "use_ss": [1, 0], "use_sb": 0},
    "gecode_opt_sb_ss":  {"model": f"{BASE_DIR}/cp_rr_opt.mzn",   "solver": "gecode", "opt": True,  "use_ss": [1, 0], "use_sb": 1},
    "chuffed_opt_reg_ss":{"model": f"{BASE_DIR}/cp_rr_opt.mzn",   "solver": "chuffed","opt": True,  "use_ss": [1, 0], "use_sb": 0},
    "chuffed_opt_sb_ss": {"model": f"{BASE_DIR}/cp_rr_opt.mzn",   "solver": "chuffed","opt": True,  "use_ss": [1, 0], "use_sb": 1},
    "cp_opt_reg_ss":     {"model": f"{BASE_DIR}/cp_rr_opt.mzn",   "solver": "cp",     "opt": True,  "use_ss": [1, 0], "use_sb": 0},
    "cp_opt_sb_ss":      {"model": f"{BASE_DIR}/cp_rr_opt.mzn",   "solver": "cp",     "opt": True,  "use_ss": [1, 0], "use_sb": 1},
}

UNSAT_TEMPLATE = {
    "time": TIME_LIMIT,
    "optimal": False,
    "obj": None,
    "sol": [],
}


def load_existing(json_path: Path) -> dict:
    if json_path.exists() and json_path.stat().st_size > 0:
        try:
            return json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_json(json_path: Path, data: dict) -> None:
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def seconds_from_stats(stats) -> int:
    st = stats.get("solveTime", None)
    if st is None:
        return TIME_LIMIT

    if hasattr(st, "total_seconds"):
        return max(0, int(st.total_seconds()))

    try:
        return max(0, int(st))
    except Exception:
        return TIME_LIMIT


def run_model(model_file: str, solver_name: str, n: int, ss, sb: int, opt: bool):
    model = minizinc.Model(model_file)
    solver = minizinc.Solver.lookup(solver_name)
    inst = minizinc.Instance(solver, model)

    inst["n"] = n

    # RR pairings
    t0 = time.perf_counter()
    weeks = circle_method_pairs(n)
    rr_time = time.perf_counter() - t0

    inst["pair"] = [[[a, b] for (a, b) in week] for week in weeks]


    # toggles
    inst["use_ss"] = ss[0]
    inst["use_sb"] = sb

    with contextlib.redirect_stderr(io.StringIO()):
        result = inst.solve(timeout=timedelta(seconds=TIME_LIMIT))

    t = seconds_from_stats(result.statistics)
    t_total = t + rr_time

    if result.solution is None:
        st = getattr(result, "status", None)
        st_str = str(st).lower() if st is not None else ""
        if "unsat" in st_str:
            return t_total, "unsat", dict(UNSAT_TEMPLATE)
        return TIME_LIMIT, "timeout", dict(UNSAT_TEMPLATE)

    out_str = result.solution._output_item
    output_item = eval(out_str)

    if opt:
        sol = output_item.get("sol", [])
        obj = output_item.get("obj", None)
        optimal_flag = output_item.get("optimal", True)
    else:
        sol = output_item
        obj = None
        optimal_flag = True

    payload = {
        "time": int(t),
        "optimal": optimal_flag,
        "obj": obj,
        "sol": sol,
    }
    return int(t), "sat", payload


def filter_models(models: dict) -> dict:
    # 1) If -models is provided, run exactly those keys(overrides everything else)
    if args.models.strip():
        wanted = [k.strip() for k in args.models.split(",") if k.strip()]
        missing = [k for k in wanted if k not in models]
        if missing:
            print(f"Warning: unknown model keys ignored: {missing}")
        return {k: models[k] for k in wanted if k in models}

    out = dict(models)

    # 2) Solver filter
    if args.solver:
        allowed = set(args.solver)
        out = {k: v for k, v in out.items() if v.get("solver") in allowed}

    # 3) Decision/Opt filter
    if args.decision and not args.opt:
        out = {k: v for k, v in out.items() if not v.get("opt", False)}
    elif args.opt and not args.decision:
        out = {k: v for k, v in out.items() if v.get("opt", False)}
    # if both provided or none provided - no filtering

    # 4) Symmetry breaking filter
    if args.sb is not None:
        out = {k: v for k, v in out.items() if int(v.get("use_sb", 0)) == int(args.sb)}

    # 5) Search strategy filter (based on use_ss[0])
    if args.ss is not None:
        out = {k: v for k, v in out.items() if int(v.get("use_ss", [0, 0])[0]) == int(args.ss)}

    return out


def main():

    any_filters = any([
        args.solver is not None,
        args.decision,
        args.opt,
        args.sb is not None,
        args.ss is not None,
        bool(args.models.strip()),
    ])

    if args.n == 0 or any_filters:
        model_names = filter_models(MODEL_NAMES)
    else:
        mod_type = int(
            input(
                "Select the models to run \n"
                " 1. Decision Models \n"
                " 2. Optimization Models \n"
                " 3. All\n\n"
                "option: "
            )
        )
        if mod_type == 1:
            model_names = {k: v for k, v in MODEL_NAMES.items() if not v.get("opt", False)}
        elif mod_type == 2:
            model_names = {k: v for k, v in MODEL_NAMES.items() if v.get("opt", False)}
        else:
            model_names = MODEL_NAMES

        model_names = filter_models(model_names)

    if not model_names:
        print("No models selected (filters removed everything).")
        return

    for n in N_VALUES:
        json_path = OUTPUT_DIR / f"{n}.json"
        existing = load_existing(json_path)

        print(f"\n=== CP n={n} ===")

        for model_name, model_data in model_names.items():
            t, st, payload = run_model(
                model_data["model"],
                model_data["solver"],
                n,
                model_data["use_ss"],
                model_data["use_sb"],
                model_data["opt"],
            )

            existing[model_name] = payload
            save_json(json_path, existing)

            print(f"[{model_name}] status={st} time={t:.3f}s")

        print(f"Wrote results to {json_path}")


if __name__ == "__main__":
    main()
