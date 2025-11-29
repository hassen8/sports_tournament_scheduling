import time
from pathlib import Path
import pyomo.environ as pyo

from mip_plain import plain_model
from mip_symmetry import symmetry_model
from mip_implied import implied_model
from mip_op import opt_model

from utils_json import write_result_json

def solve_model(m, solver_name="highs", time_limit=300):

    solver = pyo.SolverFactory(solver_name)

    if solver is None:
        return None, False

    if solver_name == "highs":
        solver.options["time_limit"] = time_limit

    elif solver_name == "cbc":
        solver.options["seconds"] = time_limit
        solver.options["threads"] = 1

    elif solver_name == "cplex":
        solver.options["timelimit"] = time_limit
        solver.options["randomseed"] = 0


    try:
        start = time.time()
        result = solver.solve(
            m,
            tee=False,
            load_solutions=False,
            symbolic_solver_labels=False
        )

        elapsed = time.time() - start
        if result.solver.status != pyo.SolverStatus.ok:
            return elapsed, False

        status = str(result.solver.termination_condition).lower()
        is_optimal = ("optimal" in status)

        if is_optimal:
            try:
                m.solutions.load_from(result)
            except:
                return elapsed, False

        return elapsed, is_optimal

    except Exception:
        return None, False

def extract_solution(m, n):
    sched = [[None] * (n - 1) for _ in range(n // 2)]
    for p in range(1, n // 2 + 1):
        for w in range(1, n):
            for i in range(1, n + 1):
                for j in range(1, n + 1):
                    try:
                        if i != j and pyo.value(m.y[i, j, w, p]) > 0.5:
                            sched[p - 1][w - 1] = [i, j]
                            break
                    except:
                        continue
    return sched

def run_all(n):

    models = {
        "MIP_plain": plain_model,
        "MIP_symmetry": symmetry_model,
        "MIP_implied": implied_model,
        "MIP_opt": opt_model,
    }

    solvers = ["highs", "cbc", "cplex"]

    results = {}

    print(f"\nRunning all models for n = {n}...\n")

    for model_name, fn in models.items():
        for solver_name in solvers:

            tag = f"{model_name}_{solver_name}"
            print(f"  → {tag}")

            try:
                m = fn(n)
                elapsed, ok = solve_model(m, solver_name=solver_name)

                if not ok:
                    print("     ✗ No solution")
                    results[tag] = {
                        "time": 300,
                        "optimal": False,
                        "obj": None,
                        "sol": []
                    }
                    continue

                obj = None
                if hasattr(m, "obj"):
                    try:
                        obj = int(pyo.value(m.obj))
                    except:
                        obj = None

                sol = extract_solution(m, n)

                print("     ✓ Solution found")

                results[tag] = {
                    "time": int(min(elapsed, 300)),
                    "optimal": True,
                    "obj": obj,
                    "sol": sol
                }

            except:
                print("     ✗ No solution")
                results[tag] = {
                    "time": 300,
                    "optimal": False,
                    "obj": None,
                    "sol": []
                }

    outdir = Path("../../res/MIP")
    outdir.mkdir(parents=True, exist_ok=True)
    outfile = outdir / f"{n}.json"

    write_result_json(str(outfile), full_data=results)

    print(f"\nSaved: {outfile}\n")

if __name__ == "__main__":
    for n in [6, 8, 10, 12, 14]:
        run_all(n)
