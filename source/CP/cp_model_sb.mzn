include "lex_less.mzn";
include "alldifferent.mzn";
include "global_cardinality_low_up.mzn";
include "global_cardinality.mzn";

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

% match[w,p,1] = home team, match[w,p,2] = away team
array[Weeks, Periods, 1..2] of var Teams: match;

% =====================
% Constraints
% =====================

% 1. each team plays exactly once per week
constraint forall(w in Weeks)(
    alldifferent([match[w,p,s] | p in Periods, s in 1..2]) 
);

% 2. each team plays at most twice in the same period
constraint forall(p in Periods)(
    global_cardinality_low_up(
        [match[w,p,s] | w in Weeks, s in 1..2], 
        Teams,                                  
        [0 | t in Teams],                      
        [2 | t in Teams]                      
    )
);

% 3. each pair of teams plays exactly once
constraint forall(t in Teams) (
    alldifferent( [ sum(p in Periods)(
                      if match[w,p,1] == t then match[w,p,2] 
                      else if match[w,p,2] == t then match[w,p,1] 
                      else 0 
                      endif 
                      endif ) | w in Weeks ]));

% =========================
% Symmetry Breaking
% =========================

% Fix the first week
constraint forall(p in Periods)(
    match[1,p,1] = 2*p - 1 /\ match[1,p,2] = 2*p
);

% Lexicographic ordering between consecutive weeks
constraint forall(w in 1..(n-2)) (
    lex_less([match[w,p,s] | p in Periods, s in 1..2],
             [match[w+1,p,s] | p in Periods, s in 1..2])
);

% =====================
% Solve 
% =====================

int: use_ss;

solve :: 
    if use_ss == 1 then
        int_search(
            match,
            dom_w_deg,       
            indomain_random 
        )
        :: restart_geometric(1.5, 500) 
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
