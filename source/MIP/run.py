import argparse
import time
from pathlib import Path
from amplpy import AMPL
from utils_json import write_result_json

MODEL_FILES = {
    "MIP_plain":     "source/MIP/sts_plain.mod",
    "MIP_symmetry":  "source/MIP/sts_symmetry.mod",
    "MIP_implied":   "source/MIP/sts_implied.mod",
    "MIP_opt":       "source/MIP/sts_opt.mod",
}

SOLVERS = ["gurobi", "cplex"]


def solve_ampl(model_file, solver_name, n):
    ampl = AMPL()


    ampl.setOption("solver_msg", 0)
    ampl.setOption("show_stats", 0)
    ampl.setOption("display_precision", 0)

    
    ampl.setOption("gurobi_options",
                    "timelimit=300 mipgap=0 outlev=0 threads=1 seed=0")

    ampl.setOption("cplex_options",
                   "timelimit=300 mipgap=0 display=0 threads=1 deterministic=1 randomseed=0")

    
    ampl.read(model_file)
    ampl.eval(f"let n := {n};")
    ampl.eval(f"option solver {solver_name};")

    
    start = time.time()
    ampl.solve()
    elapsed = time.time() - start

    
    result = str(ampl.getValue("solve_result")).lower()
    result_num = int(ampl.getValue("solve_result_num"))

    
    if "error" in result or result_num >= 500:
        return elapsed, False, None, []

    if "limit" in result or result_num == 400:
        return 300, False, None, []

    
    try:
        obj = ampl.getObjective("FairnessObjective").value()
    except:
        obj = None

    
    sol = extract_schedule(ampl, n)

    if sol == []:
        return elapsed, False, obj, []

    return elapsed, True, obj, sol



def extract_schedule(ampl, n):
    """
    Extracts matches in format:
    sched[p][w] = [i, j]
    """
    try:
        vals = ampl.getVariable("x").getValues()
    except:
        return []

    sched = [[None for _ in range(n - 1)] for _ in range(n // 2)]

    for (i, j, w, p), val in vals.to_dict().items():
        if val > 0.5:
            sched[p - 1][w - 1] = [int(i), int(j)]

  
    has_match = any(any(slot is not None for slot in row) for row in sched)
    if not has_match:
        return []

    return sched



def run_all(n):
    results = {}

    print(f"\nRunning AMPL models for n = {n}...\n")

    for model_name, file_name in MODEL_FILES.items():
        for solver_name in SOLVERS:

            tag = f"{model_name}_{solver_name}"
            print(f"  → {tag}")

            elapsed, optimal, obj, sol = solve_ampl(file_name, solver_name, n)

            if not optimal:
                print("     ✗ No valid solution")
                results[tag] = {
                    "time": int(min(elapsed, 300)),
                    "optimal": False,
                    "obj": None,
                    "sol": []
                }
            else:
                print("     ✓ Solution found")
                results[tag] = {
                    "time": int(min(elapsed, 300)),
                    "optimal": True,
                    "obj": obj,
                    "sol": sol
                }

    out = Path("res/MIP")
    out.mkdir(parents=True, exist_ok=True)
    outfile = out / f"{n}.json"

    write_result_json(str(outfile), full_data=results)
    print(f"\nSaved: {outfile}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run MIP optimization models.")
    parser.add_argument("-n", type=int, help="Instance size to run. Pass 0 to run all default instances.")
    
    args = parser.parse_args()
    inst = int(args.n) 

    
    if inst == 0:
        default_instances = [6, 8, 10, 12, 14, 16]
        print(f"Argument is 0. Running all default instances: {default_instances}")
        for n in default_instances:
            run_all(n)
    else:
        print(f"Running specific instance: n = {inst}")

        run_all(inst)
