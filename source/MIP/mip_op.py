"""
MIP model for the STS problem with:
  - constraints,
  - symmetry breaking,
  - implied constraints.
  - fairness objective: minimize the maximum home/away imbalance.
"""
import pyomo.environ as pyo

def opt_model(n):
    m = pyo.ConcreteModel()

    m.T = pyo.Set(initialize=range(1, n + 1))       # Teams
    m.W = pyo.Set(initialize=range(1, n))           # Weeks
    m.P = pyo.Set(initialize=range(1, n // 2 + 1))   # Periods per week

    m.y = pyo.Var(m.T, m.T, m.W, m.P, domain=pyo.Binary)

    # No self matches
    m.no_self = pyo.ConstraintList()
    for i in m.T:
        for w in m.W:
            for p in m.P:
                m.no_self.add(m.y[i, i, w, p] == 0)

    # One match per (week, period)
    def slot_match_rule(m, w, p):
        return sum(m.y[i, j, w, p] for i in m.T for j in m.T if i != j) == 1
    m.slot_match = pyo.Constraint(m.W, m.P, rule=slot_match_rule)

    # Each pair meets exactly once
    m.once = pyo.ConstraintList()
    for i in m.T:
        for j in m.T:
            if i < j:
                m.once.add(
                    sum(m.y[i, j, w, p] + m.y[j, i, w, p] for w in m.W for p in m.P) == 1
                )

    # Each team plays once per week
    def weekly_rule(m, t, w):
        return sum(m.y[t, j, w, p] + m.y[j, t, w, p] for j in m.T for p in m.P if j != t) == 1
    m.weekly_game = pyo.Constraint(m.T, m.W, rule=weekly_rule)

    # Each team appears at most twice in any period
    def period_limit_rule(m, t, p):
        return sum(m.y[t, j, w, p] + m.y[j, t, w, p] for j in m.T for w in m.W if j != t) <= 2
    m.period_limit = pyo.Constraint(m.T, m.P, rule=period_limit_rule)

    # Fix first week matches
    def week1_rule(m, p):
        return m.y[2*p - 1, 2*p, 1, p] == 1
    m.week1 = pyo.Constraint(m.P, rule=week1_rule)

    # Each team plays n-1 matches total
    def total_matches_rule(m, t):
        return sum(m.y[t, j, w, p] + m.y[j, t, w, p] 
                   for j in m.T for w in m.W for p in m.P if j != t) == n - 1
    m.total_matches = pyo.Constraint(m.T, rule=total_matches_rule)

    # Each period has n - 1 matches
    def matches_in_period_rule(m, p):
        return sum(m.y[i, j, w, p] 
                   for i in m.T for j in m.T for w in m.W if i != j) == n - 1
    m.period_total = pyo.Constraint(m.P, rule=matches_in_period_rule)

    # Variables for home/away tracking
    m.h = pyo.Var(m.T, domain=pyo.NonNegativeIntegers, bounds=(0, n - 1))
    m.a = pyo.Var(m.T, domain=pyo.NonNegativeIntegers, bounds=(0, n - 1))
    m.d = pyo.Var(m.T, domain=pyo.NonNegativeIntegers, bounds=(0, n - 1))
    m.F = pyo.Var(domain=pyo.NonNegativeIntegers, bounds=(0, n - 1))

    # Home/away balance
    m.home_count = pyo.Constraint(m.T, rule=lambda m, t:
        m.h[t] == sum(m.y[t, j, w, p] for j in m.T for w in m.W for p in m.P if j != t))

    m.away_count = pyo.Constraint(m.T, rule=lambda m, t:
        m.a[t] == sum(m.y[j, t, w, p] for j in m.T for w in m.W for p in m.P if j != t))

    m.diff1 = pyo.Constraint(m.T, rule=lambda m, t: m.d[t] >= m.h[t] - m.a[t])
    m.diff2 = pyo.Constraint(m.T, rule=lambda m, t: m.d[t] >= m.a[t] - m.h[t])
    m.max_diff = pyo.Constraint(m.T, rule=lambda m, t: m.F >= m.d[t])

    m.obj = pyo.Objective(expr=m.F, sense=pyo.minimize)

    return m
