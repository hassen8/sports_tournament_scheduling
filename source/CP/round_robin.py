#!/usr/bin/env python3
"""
Round-robin pairings (circle method) for even n.
weeks[w] = list of P matches (a,b) with a<b
"""

def circle_method_pairs(n: int):
    if n % 2 != 0:
        raise ValueError("n must be even")

    teams = list(range(1, n + 1))
    fixed = teams[-1]
    rot = teams[:-1]

    W = n - 1
    P = n // 2
    half = n // 2

    weeks = []
    for _w in range(W):
        left = rot[:half - 1] + [fixed]
        right = rot[half - 1:][::-1]

        pairs = []
        for a, b in zip(left, right):
            if a < b:
                pairs.append((a, b))
            else:
                pairs.append((b, a))
        weeks.append(pairs)

        # rotate
        rot = [rot[-1]] + rot[:-1]

    return weeks

circle_method_pairings = circle_method_pairs
