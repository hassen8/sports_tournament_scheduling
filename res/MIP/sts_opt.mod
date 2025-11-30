############################################################
#          STS FAIRNESS MODEL (AMPL version of opt_model)
# Includes:
#   - basic constraints
#   - symmetry breaking
#   - implied constraints
#   - fairness objective: minimize max home/away imbalance
############################################################

# Number of teams
param n >= 2, integer;

# Sets
set T := 1..n;
set W := 1..n-1;
set P := 1..n div 2;

# Decision variable (DIRECTED):
# x[i,j,w,p] = 1 if team i HOSTS team j in week w, period p
var x {i in T, j in T, w in W, p in P} binary;

# No team can play itself
subject to NoSelf {i in T, w in W, p in P}:
    x[i, i, w, p] = 0;


############################################################
# 1) One match per (week, period)
#    Exactly one directed match per slot
############################################################
subject to OneMatchPerSlot {w in W, p in P}:
    sum {i in T, j in T: i != j} x[i, j, w, p] = 1;


############################################################
# 2) Each pair meets exactly once (unordered pair)
############################################################
subject to MeetOnce {i in T, j in T: i < j}:
    sum {w in W, p in P} (x[i, j, w, p] + x[j, i, w, p]) = 1;


############################################################
# 3) Each team plays once per week
############################################################
subject to WeeklyGame {t in T, w in W}:
      sum {j in T, p in P: j != t} x[t, j, w, p]
    + sum {i in T, p in P: i != t} x[i, t, w, p]
    = 1;


############################################################
# 4) Each team appears at most twice in any period
############################################################
subject to PeriodLimit {t in T, p in P}:
      sum {j in T, w in W: j != t} x[t, j, w, p]
    + sum {i in T, w in W: i != t} x[i, t, w, p]
    <= 2;


############################################################
# 5) Symmetry breaking (fix week 1)
# Period 1: (1,2)
# Period 2: (3,4)
# Period 3: (5,6)
# ...
############################################################
subject to Week1Fix {p in P}:
    x[2*p - 1, 2*p, 1, p] = 1;


############################################################
# 6) Each team plays exactly n−1 matches total
############################################################
subject to TotalMatches {t in T}:
      sum {j in T, w in W, p in P: j != t} x[t, j, w, p]
    + sum {i in T, w in W, p in P: i != t} x[i, t, w, p]
    = n - 1;


############################################################
# 7) Each period has exactly n−1 matches total
#    (one match per week in that period, across n-1 weeks)
############################################################
subject to PeriodTotal {p in P}:
    sum {i in T, j in T, w in W: i != j} x[i, j, w, p] = n - 1;


############################################################
# 8) Fairness variables
############################################################
var h {T} >= 0, <= n-1, integer;       # home games
var a {T} >= 0, <= n-1, integer;       # away games
var d {T} >= 0, <= n-1, integer;       # imbalance
var F        >= 0, <= n-1, integer;    # maximum imbalance


############################################################
# 9) Home/away counts  (DIRECTED, like in Pyomo)
############################################################
subject to HomeCount {t in T}:
    h[t] =
        sum {j in T, w in W, p in P: j != t} x[t, j, w, p];

subject to AwayCount {t in T}:
    a[t] =
        sum {j in T, w in W, p in P: j != t} x[j, t, w, p];


############################################################
# 10) d[t] >= | h[t] - a[t] |
############################################################
subject to Diff1 {t in T}:
    d[t] >= h[t] - a[t];

subject to Diff2 {t in T}:
    d[t] >= a[t] - h[t];


############################################################
# 11) F >= d[t] for each team
############################################################
subject to MaxDiff {t in T}:
    F >= d[t];


############################################################
# Objective: minimize maximum imbalance
############################################################
minimize FairnessObjective:
    F;
