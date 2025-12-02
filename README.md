# 🧩 CDMO Optimization Project

This project provides a **unified containerized environment** for running multiple optimization approaches — **CP (Constraint Programming)**, **MIP (Mixed Integer Programming)**, and **SMT (Satisfiability Modulo Theories)** — using **MiniZinc** and **Python**.  

Each approach runs its own solver logic and saves results to a corresponding folder under `/res`.

---

## 🗂️ Project Structure

```
project/
│
├── source/ # Source code for each approach
│ ├── CP/
│ ├── MIP/
│ └── SMT/
│
├── res/ # Output directory (results stored here)
│ ├── CP/
│ ├── MIP/
│ └── SMT/
│
├── entrypoint.sh # Main entrypoint controlling which approach to run
└── Dockerfile # Docker build configuration
```

## ⚙️ Requirements

- [Docker](https://www.docker.com/get-started) installed on your system  
- (Optional) `git` if you’re cloning the repository

---

## 🏗️ Building the Docker Image

From the root of the project, run:

```bash 
docker build -t sts .
```

This will:
- Install Python 3.11 and MiniZinc 2.9.4 inside the container
- Copy the project files
- Make entrypoint.sh the container’s default entrypoint

### 1. Run all approaches
To run the container:
```bash
docker run --rm -v "$(pwd)/source:/sports_tournament_scheduling/source" -v "$(pwd)/res:/sports_tournament_scheduling/res" -it sts
```
This will run the Approach wizard, which will let you choose which approach you want to run and the number of the instance size
~~~

### 2. Run specific approach
```bash
docker run --rm -v "$(pwd)/source:/sports_tournament_scheduling/source" -v "$(pwd)/res:/sports_tournament_scheduling/res" -it sts --approach CP
```

### 3. Run specific approach with instance size
```bash
docker run --rm -v "$(pwd)/source:/sports_tournament_scheduling/source" -v "$(pwd)/res:/sports_tournament_scheduling/res" -it sts --approach CP --instance 10
```

### Run solution checker:

```bash
python "$(pwd)/soulution_checker.py" 'res/CP'
```
