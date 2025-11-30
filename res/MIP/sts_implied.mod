############################################################
#  STS IMPLIED MODEL  (AMPL version of mip_implied.py)
############################################################

# Number of teams
param n >= 2, integer;

# Sets
set T := 1..n;
set W := 1..n-1;
set P := 1..n div 2;

# Decision variable: only i<j
var x {i in T, j in T, w in W, p in P: i < j} binary;

############################################################
# 1) One match per (week, period)
############################################################
subject to OneMatchPerSlot {w in W, p in P}:
    sum {i in T, j in T: i < j} x[i, j, w, p] = 1;

############################################################
# 2) Each pair meets once
############################################################
subject to MeetOnce {i in T, j in T: i < j}:
    sum {w in W, p in P} x[i, j, w, p] = 1;

############################################################
# 3) Each team plays once per week  (FIXED)
############################################################
subject to WeeklyGame {t in T, w in W}:
      sum {j in T, p in P: j > t} x[t, j, w, p]
    + sum {i in T, p in P: i < t} x[i, t, w, p]
    = 1;

############################################################
# 4) Each team appears ≤2 times in any period  (FIXED)
############################################################
subject to PeriodLimit {t in T, p in P}:
      sum {j in T, w in W: j > t} x[t, j, w, p]
    + sum {i in T, w in W: i < t} x[i, t, w, p]
    <= 2;

############################################################
# 5) Fix first-week matches   (symmetry-breaking)
############################################################
subject to Week1Fix {p in P}:
    x[2*p - 1, 2*p, 1, p] = 1;

############################################################
# 6) Each team plays n-1 total matches  (implied)
############################################################
subject to TotalMatches {t in T}:
      sum {j in T, w in W, p in P: j > t} x[t, j, w, p]
    + sum {i in T, w in W, p in P: i < t} x[i, t, w, p]
    = n - 1;

############################################################
# 7) Each period has n-1 matches total  (implied)
############################################################
subject to PeriodTotal {p in P}:
    sum {i in T, j in T, w in W: i < j} x[i, j, w, p] = n - 1;

# Feasibility objective
minimize DummyObj: 0;
