# source/SMT_LIA/smt_lia_decode.py
#
# Decode QF-LIA SMT solver output into schedule matrix.
# We look for lines of the form:
#   (define-fun H_i_j_Pp_Ww () Int 1)

import re


def decode_smt_lia_model(output_text, n):
    pattern = re.compile(
        r"\(define-fun\s+H_(\d+)_(\d+)_P(\d+)_W(\d+)\s*\(\)\s*Int\s+1",
        re.IGNORECASE,
    )

    assignments = []

    for line in output_text.splitlines():
        m = pattern.search(line)
        if m:
            i = int(m.group(1))
            j = int(m.group(2))
            p = int(m.group(3))
            w = int(m.group(4))
            assignments.append((i, j, p, w))

    periods = n // 2
    weeks = n - 1

    sol = [[None for _ in range(weeks)] for _ in range(periods)]

    for (i, j, p, w) in assignments:
        sol[p - 1][w - 1] = [i, j]

    return sol
