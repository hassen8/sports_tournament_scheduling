# fix_null_solutions.py
import json, os

for f in os.listdir("res/SAT"):
    if f.endswith(".json"):
        path = os.path.join("res/SAT", f)
        data = json.load(open(path))

        changed = False
        for k,v in data.items():
            if v.get("sol") is None:
                v["sol"] = []
                changed = True

        if changed:
            json.dump(data, open(path, "w"), indent=2)
            print("Fixed:", path)
