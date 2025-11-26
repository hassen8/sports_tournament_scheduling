include "global_cardinality_low_up.mzn";
include "all_different.mzn";

% =====================
% Parameters
% =====================
int: n;


set of int: Teams = 1..n;
set of int: Weeks = 1..(n-1);
set of int: Periods = 1..(n div 2);

% =====================
% Decision Variables
% =====================

% match view: Who plays in which slot?
% match[w,p,1] = home team, match[w,p,2] = away team
array[Weeks, Periods, 1..2] of var Teams: match;

% Opponent view: Who is Team T's opponent in Week W?
array[Teams, Weeks] of var Teams: opponent;

% =====================
% Constraints
% =====================

% 1. link both views (Channeling Constraint)
constraint forall(w in Weeks, p in Periods)(
    opponent[match[w,p,1], w] = match[w,p,2] /\
    opponent[match[w,p,2], w] = match[w,p,1]
);

% 2. A team cannot play itself (self constraint)
constraint forall(t in Teams, w in Weeks)(
    opponent[t,w] != t
);

% 3. Every team plays every other team exactly once
constraint forall(t in Teams)(
    alldifferent( [opponent[t,w] | w in Weeks] )
);

% 4. Each team plays exactly once per week
constraint forall(w in Weeks)(
    alldifferent([match[w,p,s] | p in Periods, s in 1..2])
);

% 5. A Team plays at most twice in a period
constraint forall(p in Periods)(
    global_cardinality_low_up(
        [match[w,p,s] | w in Weeks, s in 1..2],
        Teams,
        [0 | t in Teams],
        [2 | t in Teams]
    )
);


% =====================
% Symmetry Breaking
% =====================

% 1. fix the first week.
constraint forall(p in Periods)(
    match[1, p, 1] = (p * 2) - 1 /\
    match[1, p, 2] = (p * 2)
);

% 2. Fix the first slot of the first period in every week.
constraint forall(w in Weeks where match[w,1,1] == 1 \/ match[w,1,2] == 1)(
    match[w,1,1] = 1
);

% 3. force the first slot of every week to order home < away
constraint forall(w in Weeks, p in Periods)(
    match[w,p,1] < match[w,p,2]
);


% =====================
% Solve/ search stratefy 
% =====================


int: use_ss;
int: use_dwd;

solve :: 
    if use_ss == 1 then
        seq_search([
      % fix the home team first
      int_search(
          [match[w,p,1] | w in Weeks, p in Periods], 
          if use_dwd==0 then first_fail else dom_w_deg endif,      
          if use_dwd==0 then indomain_split else indomain_random endif
      ),
      % then fix the away team
      int_search(
          [match[w,p,2] | w in Weeks, p in Periods],
          first_fail,      
          indomain_min
            )
          ])
          :: restart_geometric(1.5,500)
     endif
     satisfy;


% =====================
% Output 
% =====================

output [
  " [\n" ++
  concat([
    "  [" ++ concat([
        "[" ++ show(match[w,p,1]) ++ "," ++ show(match[w,p,2]) ++ "]"
        ++ ( if w < max(Weeks) then "," else "" endif )
      | w in Weeks]) ++ "]"
    ++ ( if p < max(Periods) then ",\n" else "\n" endif )
  | p in Periods]) ++
  " ]\n"
];