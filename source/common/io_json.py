import json
from pathlib import Path

def write_result_json(approach_name, n, json_path, solve_time, optimal, solution_matrix, obj=None):
    """
    Write/update JSON entry for this solver.

    This function:
      - loads existing JSON,  if there are any)
      - inserts/updates only this solver key
      - ensures valid format
    """

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

    # Always use the same naming convention
    key = f"{approach_name}_{n}"

    data[key] = {
        "time": int(solve_time),
        "optimal": bool(optimal),
        "obj": obj if obj is not None else None,
        "sol": solution_matrix if solution_matrix is not None else []
    }

    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)
