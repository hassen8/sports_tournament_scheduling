import json
import math
from pathlib import Path

def write_result_json(path, approach_name=None, runtime=None, optimal=None, obj=None, sol_matrix=None, full_data=None):
   
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    if full_data is not None:
        with open(path, "w") as f:
            json.dump(full_data, f, indent=2)
        print(f"JSON written to: {path}")
        return
    data = {
        approach_name: {
            "time": int(math.floor(runtime)),
            "optimal": bool(optimal),
            "obj": None if obj is None else int(obj),
            "sol": sol_matrix
        }
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"JSON written to: {path}")
