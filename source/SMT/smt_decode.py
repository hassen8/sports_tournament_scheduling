import re

def decode_smt_model(model_str: str, n: int):
    """
    Decode a model produced by Yices or OpenSMT into the schedule matrix.
    Supports both formats:

    YICES:
      (define-fun M_1_2_P0_W0 () Bool true)

    OPENSMT:
      ((M_1_2_P0_W0 true))

    Returns:
        sol[p][w] = [home, away]
    """

    periods = n // 2
    weeks = n - 1

    M_vals = {}
    H_vals = {}

    lines = [ln.strip() for ln in model_str.splitlines() if ln.strip()]
    text = model_str.replace("\n", " ")

    # 1) Extract Yices-style define-fun
    yices_defs = re.findall(
        r"\(define-fun\s+([A-Za-z0-9_]+)\s*\(\)\s*Bool\s+(true|false)\)",
        text,
        flags=re.IGNORECASE
    )

    for name, val in yices_defs:
        val = val.lower() == "true"
        m = re.match(r"([MH])_(\d+)_(\d+)_P(\d+)_W(\d+)", name)
        if m:
            kind = m.group(1)
            ti = int(m.group(2))
            tj = int(m.group(3))
            p = int(m.group(4))
            w = int(m.group(5))
            key = (ti, tj, p, w)
            if kind == "M":
                M_vals[key] = val
            else:
                H_vals[key] = val

    # 2) Extract OpenSMT-style entries
   
    opensmt_defs = re.findall(
        r"\(\s*([A-Za-z0-9_]+)\s+(true|false)\s*\)",
        text,
        flags=re.IGNORECASE
    )

    for name, val in opensmt_defs:
        val = val.lower() == "true"
        m = re.match(r"([MH])_(\d+)_(\d+)_P(\d+)_W(\d+)", name)
        if m:
            kind = m.group(1)
            ti = int(m.group(2))
            tj = int(m.group(3))
            p = int(m.group(4))
            w = int(m.group(5))
            key = (ti, tj, p, w)
            if kind == "M":
                M_vals[key] = val
            else:
                H_vals[key] = val


    # 3) Build schedule matrix
   
    sol = [[None for _ in range(weeks)] for _ in range(periods)]

    for (ti, tj, p, w), mv in M_vals.items():
        if not mv:
            continue
        if p < 0 or p >= periods or w < 0 or w >= weeks:
            continue

        home, away = ti, tj

        # check home indicator
        key = (ti, tj, p, w)
        if key in H_vals:
            if H_vals[key] is False:
                home, away = tj, ti

        sol[p][w] = [home, away]

    return sol
