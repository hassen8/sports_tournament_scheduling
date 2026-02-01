# =====================================================
# MIP model for the Sports Tournament Scheduling (STS)
# with round-robin preprocessing
#
# Constraints enforced:
# 1. One match per (week, period)
# 2. Each pair meets exactly once        (by preprocessing)
# 3. Each team plays once per week
# 4. Each team appears at most twice in any period
# + Implied constraint to strengthen the formulation
# =====================================================


param n integer;          


set TEAMS := 1..n;
set WEEKS := 1..(n-1);
set PERIODS := 1..(n/2);


set MATCHES within TEAMS cross TEAMS cross WEEKS;

var x{(i,j,w) in MATCHES, p in PERIODS} binary;

s.t. OneMatchPerWeekPeriod {w in WEEKS, p in PERIODS}:
    sum {(i,j,w) in MATCHES} x[i,j,w,p] = 1;

s.t. OneMatchPerTeamWeek {t in TEAMS, w in WEEKS}:
    sum {(i,j,w) in MATCHES: i = t} sum {p in PERIODS} x[i,j,w,p]
  + sum {(i,j,w) in MATCHES: j = t} sum {p in PERIODS} x[i,j,w,p]
  <= 1;

s.t. PeriodLimit {t in TEAMS, p in PERIODS}:
    sum {(i,j,w) in MATCHES: i = t} x[i,j,w,p]
  + sum {(i,j,w) in MATCHES: j = t} x[i,j,w,p]
  <= 2;

s.t. FixFirstMatchToFirstPeriod:
    sum {(i,j,1) in MATCHES : i = 1 or j = 1} x[i,j,1,1] = 1;


s.t. NoThreeConsecutiveWeeksSamePeriod
    {t in TEAMS, p in PERIODS, w in 1..(n-3)}:
    sum {(i,j,ww) in MATCHES :
         ww in w..(w+2) and (i = t or j = t)}
         x[i,j,ww,p]
    <= 2;


minimize obj: 0;
