/*
MIP model for the STS problem with:
  - constraints,
  - symmetry breaking,
  - implied constraints.
  - fairness objective: minimize the maximum home/away imbalance.
*/

param n >= 2, integer;

set T := 1..n;
set W := 1..n-1;
set P := 1..n div 2;

# Variables
# x[i,j,w,p] = 1 if team i (home) plays team j (away) in week w and period p.

var x{i in T, j in T, w in W, p in P: i != j} binary;


# One match per (week, period)

subject to OneMatchPerSlot{w in W, p in P}:
    sum{i in T, j in T: i != j} x[i,j,w,p] = 1;


# Each pair of teams meets exactly once

subject to MeetOnce{i in T, j in T: i < j}:
    sum{w in W, p in P} ( x[i,j,w,p] + x[j,i,w,p] ) = 1;


# Each team plays exactly once per week

subject to WeeklyGame{t in T, w in W}:
    sum{j in T, p in P: j != t} x[t,j,w,p]
  + sum{i in T, p in P: i != t} x[i,t,w,p]
    = 1;


# Each team appears at most twice in any period

subject to PeriodLimit{t in T, p in P}:
    sum{j in T, w in W: j != t} x[t,j,w,p]
  + sum{i in T, w in W: i != t} x[i,t,w,p]
    <= 2;

# Symmetry breaking (fix week 1)

subject to Week1Fix{p in P}:
    x[2*p - 1, 2*p, 1, p] = 1;



# Implied constraint: Each team plays exactly n-1 matches in the whole season

subject to TotalMatches {t in T}:
      sum {j in T, w in W, p in P: j != t} x[t, j, w, p]
    + sum {i in T, w in W, p in P: i != t} x[i, t, w, p]
    = n - 1;


# Implied constraint: Each period has exactly n-1 matches over all weeks

subject to PeriodTotal {p in P}:
    sum {i in T, j in T, w in W: i != j} x[i, j, w, p] = n - 1;



# Fairness variables

var h {T} >= 0, <= n-1, integer;       # home games
var a {T} >= 0, <= n-1, integer;       # away games
var d {T} >= 0, <= n-1, integer;       # imbalance
var F        >= 0, <= n-1, integer;    # maximum imbalance


# Home/away counts

subject to HomeCount {t in T}:
    h[t] =
        sum {j in T, w in W, p in P: j != t} x[t, j, w, p];

subject to AwayCount {t in T}:
    a[t] =
        sum {j in T, w in W, p in P: j != t} x[j, t, w, p];


# d[t] >= | h[t] - a[t] |

subject to Diff1 {t in T}:
    d[t] >= h[t] - a[t];

subject to Diff2 {t in T}:
    d[t] >= a[t] - h[t];



# F >= d[t] for each team

subject to MaxDiff {t in T}:
    F >= d[t];



# Objective: minimize maximum imbalance

minimize FairnessObjective:
    F;
