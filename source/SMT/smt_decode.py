# source/SMT/smt_decode.py
#
# Decode SMT solver model output (SMT-LIB) into the schedule matrix.
#
# Expects model output with fragments like:
#   (define-fun H_1_2_P1_W1 () Bool true)
#   or with 'true' on the next line.
#
# Returns:
#   sol: (n/2) x (n-1) matrix of [home, away] pairs.

import re


def decode_smt_model(output_text, n):
    """
    Parse SMT solver 'model' output and reconstruct the schedule
    into the matrix format required by the solution checker.

    Args:
        output_text : raw stdout of the SMT solver
        n           : number of teams

    Returns:
        sol (periods x weeks matrix), each entry [home, away],
        or a matrix full of None if no TRUE assignments were found.
    """
    if not output_text:
        # No output at all
        periods = n // 2
        weeks = n - 1
        return [[None for _ in range(weeks)] for _ in range(periods)]

    # Regex for:
    #   (define-fun H_i_j_Pp_Ww () Bool true)
    # possibly with "true" on the next line or with extra spaces
    pattern = re.compile(
        r"\(define-fun\s+H_(\d+)_(\d+)_P(\d+)_W(\d+)\s*"
        r"\(\)\s*Bool\s*(?:\n|\r|\r\n|\s)*true\b",
        re.IGNORECASE | re.DOTALL,
    )

    assignments = []

    for match in pattern.finditer(output_text):
        i = int(match.group(1))
        j = int(match.group(2))
        p = int(match.group(3))
        w = int(match.group(4))
        assignments.append((i, j, p, w))

    periods = n // 2
    weeks = n - 1

    # Initialize empty schedule
    sol = [[None for _ in range(weeks)] for _ in range(periods)]

    for (i, j, p, w) in assignments:
        # indices in model are 1-based; matrix is 0-based
        if 1 <= p <= periods and 1 <= w <= weeks:
            sol[p - 1][w - 1] = [i, j]

    return sol
