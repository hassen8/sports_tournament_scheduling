import json
from pathlib import Path

def write_result_json(approach_name, json_path, solve_time, status, solution_matrix, obj=None):

    json_path = Path(json_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    if json_path.exists():
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
        except Exception:
            data = {}
    else:
        data = {}

    if status == "sat":
        entry = {
            "time": int(min(solve_time, 300)),
            "optimal": True,
            "obj": obj,
            "sol": solution_matrix
        }
    elif status == "unsat":
        entry = {
            "time": int(min(solve_time, 300)),
            "optimal": True,
            "obj": None,
            "sol": []
        }
    else:
        entry = {
            "time": 300,
            "optimal": False,
            "obj": None,
            "sol": []
        }

    data[approach_name] = entry

    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)
