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

SOLVERS = ["highs", "gurobi", "cplex"]


def solve_ampl(model_file, solver_name, n):
    ampl = AMPL()

   
    ampl.setOption("solver_msg", 0)
    ampl.setOption("show_stats", 0)
    ampl.setOption("display_precision", 0)
    ampl.setOption("presolve", 1)

 
    ampl.setOption("highs_options",  "time_limit=300 output_flag=0 log_to_console=0")
    ampl.setOption("gurobi_options", "timelimit=300 outlev=0")
    ampl.setOption("cplex_options",  "timelimit=300 display=0")

    
    ampl.read(model_file)
    ampl.eval(f"let n := {n};")
    ampl.eval(f"option solver {solver_name};")

  
    start = time.time()
    ampl.solve()
    elapsed = time.time() - start

    
    status = ampl.getValue("solve_result")
    status_num = int(ampl.getValue("solve_result_num"))

   
    if status_num == 200 or "infeasible" in status.lower():
        return elapsed, True, None, []

    if status_num == 400 or "limit" in status.lower():
        return 300, False, None, []

    
    try:
        obj = ampl.getObjective("FairnessObjective").value()
    except:
        obj = None

    sol = extract_solution(ampl, n)
    return elapsed, True, obj, sol



def extract_solution(ampl, n):
    try:
        vals = ampl.getVariable("x").getValues()
    except:
        return []

    sched = [[None] * (n - 1) for _ in range(n // 2)]
    for row in vals:
        i, j, w, p, val = int(row[0]), int(row[1]), int(row[2]), int(row[3]), float(row[4])
        if val > 0.5:
            sched[p - 1][w - 1] = [i, j]

    return sched


def run_all(n):
    results = {}

    print(f"\nRunning AMPL models for n = {n}...\n")

    for model_name, file_name in MODEL_FILES.items():
        for solver_name in SOLVERS:

            tag = f"{model_name}_{solver_name}"
            print(f"  → {tag}")

            elapsed, optimal, obj, sol = solve_ampl(file_name, solver_name, n)

        
            if optimal and sol == [] and obj is None and elapsed != 300:
                print("     ✗ UNSAT proved")
                results[tag] = {
                    "time": int(elapsed),
                    "optimal": True,
                    "obj": None,
                    "sol": []
                }
                continue

           
            if not optimal and sol == [] and obj is None:
                print("     ✗ Timeout (no answer)")
                results[tag] = {
                    "time": 300,
                    "optimal": False,
                    "obj": None,
                    "sol": []
                }
                continue

            
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
    for n in [2,4,6, 8, 10, 12, 14]:
        run_all(n)
