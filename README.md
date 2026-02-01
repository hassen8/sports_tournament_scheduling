# CDMO Optimization Project — STS (Sports Tournament Scheduling)

This project provides a unified, containerized environment for solving the
Sports Tournament Scheduling (STS) problem using multiple optimization
paradigms:

- CP (Constraint Programming)
- SAT (Propositional Satisfiability)
- SMT (Satisfiability Modulo Theories)
- MIP (Mixed Integer Programming)

All approaches share the same round-robin preprocessing based on the classical
circle method. Each model is executed inside Docker to ensure full
reproducibility, and all results are written to disk in a uniform JSON format.

---

## Project Structure

project/
│
├── source/ # Implementation code
│ ├── CP/ # MiniZinc models and runners
│ ├── SAT/ # DIMACS CNF generator and SAT runner
│ ├── SMT/ # Z3 / SMT-LIB2 encodings and runners
│ └── MIP/ # MIP models and runners
│
├── res/ # Output results (JSON files)
│ ├── CP/
│ ├── SAT/
│ ├── SMT/
│ └── MIP/
│
├── entrypoint.sh # Main entrypoint selecting approach and instance
└── Dockerfile # Docker build configuration


---

## Output Format

For each instance size `n`, the solver produces one JSON file:

res/<APPROACH>/<n>.json


Each JSON entry contains:
- `time`: runtime in seconds (300 if timeout)
- `optimal`: boolean indicating whether the solution is complete/optimal
- `obj`: objective value (null for decision-only models)
- `sol`: an `(n/2) × (n−1)` matrix of `[home, away]` team pairs

This format is compatible with the provided solution checker.

---

## Requirements

- Docker
- (Optional) git

---

## Building the Docker Image

From the root of the project, run:

```bash
docker build -t sts .

The image includes Python, MiniZinc, and all required scripts for CP, SAT, SMT,
and MIP execution.

Running the Container

All runs must mount both the source and res directories so that results are
persisted on the host machine.

docker run --rm \
  -v "$(pwd)/source:/sports_tournament_scheduling/source" \
  -v "$(pwd)/res:/sports_tournament_scheduling/res" \
  -it sts

Running the Approaches
Interactive Mode

Running the container without arguments launches an interactive wizard that
asks for:

the approach to run (CP, SAT, SMT, MIP)

the instance size n

docker run --rm \
  -v "$(pwd)/source:/sports_tournament_scheduling/source" \
  -v "$(pwd)/res:/sports_tournament_scheduling/res" \
  -it sts

docker run --rm \
  -v "$(pwd)/source:/sports_tournament_scheduling/source" \
  -v "$(pwd)/res:/sports_tournament_scheduling/res" \
  -it sts --approach CP

Valid values for --approach are:

CP, SAT, SMT, MIP

Run a Specific Approach on a Single Instance

Example: run CP on instance size n = 10

docker run --rm \
  -v "$(pwd)/source:/sports_tournament_scheduling/source" \
  -v "$(pwd)/res:/sports_tournament_scheduling/res" \
  -it sts --approach CP --instance 10

Approach Details
CP — Constraint Programming

The CP approach uses MiniZinc models with fixed round-robin matchups provided
as input. The solver assigns matches to periods while enforcing all STS
constraints. Optional symmetry-breaking constraints and custom search
strategies may be enabled. Results are written to res/CP.

SAT — Propositional SAT

The SAT approach encodes the decision version of the STS problem as a pure
propositional formula. Fixed round-robin matchups are preprocessed, and the
remaining constraints are translated into CNF and exported in DIMACS format.
An external SAT solver is used to find a feasible assignment. Symmetry breaking
is supported via an anchor week. Results are written to res/SAT.

SMT — Satisfiability Modulo Theories

The SMT approach uses either a Z3 Python API encoding or an SMT-LIB2 export for
external solvers. Match-to-period assignment is decided under fixed round-robin
pairings. Symmetry breaking and optional pinning constraints can be enabled.
Both decision and fairness optimization variants are supported. Results are
written to res/SMT.

MIP — Mixed Integer Programming

The MIP approach formulates the STS problem as a linear integer program using
binary decision variables. Multiple variants are supported, including plain
feasibility, symmetry breaking, implied constraints, and a fairness optimization
model minimizing home/away imbalance. Results are written to res/MIP.

Batch Runs

To run an approach on multiple instance sizes, use a shell loop. Example for CP:

for n in 6 8 10 12 14 16 18 20 22 24; do
  docker run --rm \
    -v "$(pwd)/source:/sports_tournament_scheduling/source" \
    -v "$(pwd)/res:/sports_tournament_scheduling/res" \
    -it sts --approach CP --instance $n
done

Solution Checker

Generated schedules can be validated using the provided solution checker:

python solution_checker.py res/CP
python solution_checker.py res/SAT
python solution_checker.py res/SMT
python solution_checker.py res/MIP

Notes

A runtime of 300 indicates a timeout.

All solvers are run sequentially.

Preprocessing time is included in the reported runtime.

Results are fully reproducible via Docker.


