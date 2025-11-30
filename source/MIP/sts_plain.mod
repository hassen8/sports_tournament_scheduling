############################################################
#  STS PLAIN MODEL  (AMPL version of your Pyomo plain_model)
############################################################

# Number of teams
param n >= 2, integer;

# Sets
set T := 1..n;          # Teams
set W := 1..n-1;        # Weeks
set P := 1..n div 2;    # Periods

# Decision variable:
# x[i,j,w,p] = 1 if team i plays team j in week w period p
# Only define for i < j (unordered match)
var x {i in T, j in T, w in W, p in P: i < j} binary;

############################################################
# 1) One match per (week, period)
############################################################
subject to OneMatchPerSlot {w in W, p in P}:
    sum {i in T, j in T: i < j} x[i, j, w, p] = 1;

############################################################
# 2) Each pair of teams meets exactly once
############################################################
subject to MeetOnce {i in T, j in T: i < j}:
    sum {w in W, p in P} x[i, j, w, p] = 1;

############################################################
# 3) Each team plays once per week
############################################################
subject to WeeklyGame {t in T, w in W}:
      sum {j in T, p in P: j > t} x[t, j, w, p]
    + sum {i in T, p in P: i < t} x[i, t, w, p]
    = 1;

############################################################
# 4) Each team appears at most twice in any period
############################################################
subject to PeriodLimit {t in T, p in P}:
      sum {j in T, w in W: j > t} x[t, j, w, p]
    + sum {i in T, w in W: i < t} x[i, t, w, p]
    <= 2;

# Dummy objective (feasibility model)
minimize DummyObj: 0;
