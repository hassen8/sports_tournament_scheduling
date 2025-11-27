"""
MIP model for the STS problem
constraints:
    1. One match per (week, period)
    2. Each pair meets exactly once
    3. Each team plays once per week
    4. Each team appears at most twice in any period
"""
import pyomo.environ as pyo

def plain_model(n):
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

    # Only one match per slot
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
    
    m.obj = pyo.Objective(expr=0) 

    return m