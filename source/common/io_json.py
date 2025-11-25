import json
from pathlib import Path

def write_result_json(approach_name, n, json_path, solve_time, optimal, solution_matrix, obj=None):
    """
    Writes or updates the JSON for instance n.
    Each solver variant is written under a uniqu key.
    
    """

    json_path = Path(json_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    
    if json_path.exists():
        with open(json_path, "r") as f:
            data = json.load(f)
    else:
        data = {}

    data[f"{approach_name}_{n}"] = {
        "time": int(solve_time),
        "optimal": bool(optimal),
        "obj": obj if obj is not None else None,
        "sol": solution_matrix
    }

    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)
