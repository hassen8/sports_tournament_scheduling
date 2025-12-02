/*
MIP model for the STS problem with:
  - constraints,
  - symmetry breaking.
*/

param n >= 2, integer;

set T := 1..n;          # Teams
set W := 1..n-1;        # Weeks
set P := 1..n div 2;    # Periods per week

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

# Feasibility objective
minimize obj: 0;
