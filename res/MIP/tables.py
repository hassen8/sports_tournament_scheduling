import os
import json
from pathlib import Path

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def is_plain(k):     return k.startswith("MIP_plain")
def is_sym(k):       return k.startswith("MIP_symmetry")
def is_impl(k):      return k.startswith("MIP_implied")
def is_opt(k):       return k.startswith("MIP_opt")

def extract_n(filename):
    return int(filename.replace(".json", ""))

def main():

    input_dir = Path("./")   # folder WITH your JSON files
    json_files = sorted(
        [f for f in os.listdir(input_dir) if f.endswith(".json")],
        key=lambda x: extract_n(x)
    )

    table1 = []   # Decision models → time (300 → NA)
    table2 = []   # Optimization → obj (null → NA)
    table3 = []   # Decision models raw times
    table4 = []   # Optimization raw obj

    for jf in json_files:
        N = extract_n(jf)
        data = load_json(input_dir / jf)

        plain_keys = sorted([k for k in data.keys() if is_plain(k)])
        sym_keys   = sorted([k for k in data.keys() if is_sym(k)])
        impl_keys  = sorted([k for k in data.keys() if is_impl(k)])
        opt_keys   = sorted([k for k in data.keys() if is_opt(k)])

        row1 = [str(N)]
        for k in plain_keys + sym_keys + impl_keys:
            t = data[k].get("time", None)
            row1.append("NA" if t == 300 else str(t))
        table1.append(row1)

        row2 = [str(N)]
        for k in opt_keys:
            obj = data[k].get("obj", None)
            row2.append("NA" if obj is None else str(obj))
        table2.append(row2)
        
        row3 = [str(N)]
        for k in plain_keys + sym_keys + impl_keys:
            t = data[k].get("time", None)
            row3.append(str(t))
        table3.append(row3)
        
        row4 = [str(N)]
        for k in opt_keys:
            obj = data[k].get("obj", None)
            row4.append(str(obj))
        table4.append(row4)
    md = []

    def make_table(title, rows, header):
        out = []
        out.append(f"## {title}\n")
        out.append("| " + " | ".join(header) + " |")
        out.append("|" + " --- |" * len(header))
        for r in rows:
            out.append("| " + " | ".join(r) + " |")
        out.append("\n")
        return "\n".join(out)

    # detect headers from first JSON
    sample_data = load_json(input_dir / json_files[0])

    header1 = ["N"] + sorted([k for k in sample_data.keys()
                              if is_plain(k) or is_sym(k) or is_impl(k)])
    header2 = ["N"] + sorted([k for k in sample_data.keys() if is_opt(k)])
    header3 = header1[:]  # same keys as table 1
    header4 = header2[:]  # same keys as table 2

    md.append(make_table("Table 1 — Decision models (time, 300→NA)", table1, header1))
    md.append(make_table("Table 2 — Optimization model (obj, null→NA)", table2, header2))
    md.append(make_table("Table 3 — Decision models (raw time)", table3, header3))
    md.append(make_table("Table 4 — Optimization model (raw obj)", table4, header4))

    with open("mip_results.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print("\n✔ markdown file generated: mip_results.md\n")

if __name__ == "__main__":
    main()

