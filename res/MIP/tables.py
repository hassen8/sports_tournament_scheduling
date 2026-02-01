import os
import json
from pathlib import Path

# -----------------------------
# Load json safely
# -----------------------------
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# -----------------------------
# Detect category of model key
# -----------------------------
def is_plain(k): return k.startswith("MIP_plain")
def is_sym(k):   return k.startswith("MIP_symmetry")
def is_impl(k):  return k.startswith("MIP_implied")
def is_opt(k):   return k.startswith("MIP_opt")

# -----------------------------
# Extract numeric N from filename
# (safe version)
# -----------------------------
def extract_n(filename):
    return int(Path(filename).stem)

# -----------------------------
# MAIN SCRIPT
# -----------------------------
def main():

    input_dir = Path("res/MIP")

    json_files = sorted(
        [f for f in os.listdir(input_dir) if f.endswith(".json")],
        key=extract_n
    )

    if not json_files:
        raise RuntimeError("No JSON files found in res/MIP")

    # ------------------------------------------------------
    # Detect canonical column order FROM FIRST FILE
    # ------------------------------------------------------
    sample_data = load_json(input_dir / json_files[0])

    decision_cols = sorted(
        k for k in sample_data.keys()
        if is_plain(k) or is_sym(k) or is_impl(k)
    )

    opt_cols = sorted(
        k for k in sample_data.keys()
        if is_opt(k)
    )

    # ------------------------------------------------------
    # Storage for markdown rows
    # ------------------------------------------------------
    table1 = []   # Decision models → time (300 → NA)
    table2 = []   # Optimization → obj (None → NA)
    table3 = []   # Decision models → raw time
    table4 = []   # Optimization → raw obj

    # ------------------------------------------------------
    # PROCESS EACH JSON FILE
    # ------------------------------------------------------
    for jf in json_files:
        N = extract_n(jf)
        data = load_json(input_dir / jf)

        # ---------------- TABLE 1 ----------------
        row1 = [str(N)]
        for k in decision_cols:
            if k not in data:
                row1.append("NA")
            else:
                t = data[k].get("time", None)
                if t is None or int(t) == 300:
                    row1.append("NA")
                else:
                    row1.append(str(int(t)))
        table1.append(row1)

        # ---------------- TABLE 2 ----------------
        row2 = [str(N)]
        for k in opt_cols:
            if k not in data:
                row2.append("NA")
            else:
                obj = data[k].get("obj", None)
                row2.append("NA" if obj is None else str(obj))
        table2.append(row2)

        # ---------------- TABLE 3 ----------------
        row3 = [str(N)]
        for k in decision_cols:
            if k not in data:
                row3.append("NA")
            else:
                t = data[k].get("time", None)
                row3.append("NA" if t is None else str(int(t)))
        table3.append(row3)

        # ---------------- TABLE 4 ----------------
        row4 = [str(N)]
        for k in opt_cols:
            if k not in data:
                row4.append("NA")
            else:
                obj = data[k].get("obj", None)
                row4.append("NA" if obj is None else str(obj))
        table4.append(row4)

    # ------------------------------------------------------
    # BUILD MARKDOWN
    # ------------------------------------------------------
    def make_table(title, rows, header):
        out = []
        out.append(f"## {title}\n")
        out.append("| " + " | ".join(header) + " |")
        out.append("|" + " --- |" * len(header))
        for r in rows:
            out.append("| " + " | ".join(r) + " |")
        out.append("")
        return "\n".join(out)

    header1 = ["N"] + decision_cols
    header2 = ["N"] + opt_cols

    md = []
    md.append(make_table("Table 1 — Decision models (time, 300 → NA)", table1, header1))
    md.append(make_table("Table 2 — Optimization model (obj, null → NA)", table2, header2))
    md.append(make_table("Table 3 — Decision models (raw time)", table3, header1))
    md.append(make_table("Table 4 — Optimization model (raw obj)", table4, header2))

    # ------------------------------------------------------
    # WRITE FILE
    # ------------------------------------------------------
    output_path = input_dir / "mip_results.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"\n✔ Markdown file generated correctly: {output_path.resolve()}\n")

# ------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------
if __name__ == "__main__":
    main()
