# =====================================================
# MIP model for the Sports Tournament Scheduling (STS)
# with round-robin preprocessing
#
# Constraints enforced:
# 1. One match per (week, period)
# 2. Each pair meets exactly once        (by preprocessing)
# 3. Each team plays exactly once per week
# 4. Each team appears at most twice in any period
#
# Objective:
# Minimize the maximum home/away imbalance
# =====================================================


param n integer;          

set TEAMS := 1..n;
set WEEKS := 1..(n-1);
set PERIODS := 1..(n/2);


set MATCHES within TEAMS cross TEAMS cross WEEKS;


var x{(i,j,w) in MATCHES, p in PERIODS} binary;

var y{(i,j,w) in MATCHES, p in PERIODS} binary;

var h{TEAMS} >= 0 integer;
var a{TEAMS} >= 0 integer;

var d{TEAMS} >= 0 integer;

var F >= 0 integer;

s.t. OneMatchPerWeekPeriod {w in WEEKS, p in PERIODS}:
    sum {(i,j,w) in MATCHES} x[i,j,w,p] = 1;

s.t. OneMatchPerTeamWeek {t in TEAMS, w in WEEKS}:
    sum {(i,j,w) in MATCHES: i = t or j = t} sum {p in PERIODS} x[i,j,w,p]
    = 1;

s.t. PeriodLimit {t in TEAMS, p in PERIODS}:
    sum {(i,j,w) in MATCHES: i = t or j = t} x[i,j,w,p]
    <= 2;

s.t. OrientationLink {(i,j,w) in MATCHES, p in PERIODS}:
    y[i,j,w,p] <= x[i,j,w,p];


s.t. FixFirstMatchToFirstPeriod:
    sum {(i,j,1) in MATCHES : i = 1 or j = 1} x[i,j,1,1] = 1;

s.t. HomeCount {t in TEAMS}:
    h[t] =
        sum {(i,j,w) in MATCHES, p in PERIODS: i = t} y[i,j,w,p]
      + sum {(i,j,w) in MATCHES, p in PERIODS: j = t} (x[i,j,w,p] - y[i,j,w,p]);

s.t. AwayCount {t in TEAMS}:
    a[t] =
        sum {(i,j,w) in MATCHES, p in PERIODS: i = t} (x[i,j,w,p] - y[i,j,w,p])
      + sum {(i,j,w) in MATCHES, p in PERIODS: j = t} y[i,j,w,p];

s.t. DiffPos {t in TEAMS}:
    d[t] >= h[t] - a[t];

s.t. DiffNeg {t in TEAMS}:
    d[t] >= a[t] - h[t];

s.t. MaxDiff {t in TEAMS}:
    F >= d[t];

minimize FairnessObjective: F;
