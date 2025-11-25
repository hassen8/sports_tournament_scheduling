#!/usr/bin/env bash
set -Eeuo pipefail
trap cleanup SIGINT SIGTERM ERR EXIT

# =============================
# Configurable Parameters
# =============================
APPROACHES=("CP" "MIP" "SMT")
DEFAULT_INSTANCE=6

# =============================
# Utility Functions
# =============================
cleanup() {
  trap - SIGINT SIGTERM ERR EXIT
}

msg() {
  echo -e "[$(date '+%H:%M:%S')] ${1-}"
}

die() {
  local msg=$1
  local code=${2-1}
  echo >&2 "Error: $msg"
  exit "$code"
}

usage() {
  cat << EOF
Usage: $(basename "${BASH_SOURCE[0]}") [OPTIONS]

Options:
  -a, --approach    Approach to run (CP | MIP | SMT). Default: all available approaches
  -n, --instance    Instance size (e.g., 6, 8, 10, 12). Default: ${DEFAULT_INSTANCE}
  -h, --help        Show this help and exit

Examples:
  ./entrypoint.sh --approach CP --instance 8
  ./entrypoint.sh
EOF
  exit 0
}

# =============================
# Parse Command-Line Arguments
# =============================
parse_params() {
  SELECTED_APPROACH=""
  INSTANCE=0

  while [[ $# -gt 0 ]]; do
    case "$1" in
      -a|--approach)
        SELECTED_APPROACH="$2"
        shift 2
        ;;
      -n|--instance)
        INSTANCE="$2"
        shift 2
        ;;
      -h|--help)
        usage
        ;;
      *)
        die "Unknown option: $1"
        ;;
    esac
  done
}

# =============================
# Main Logic
# =============================
main() {
  parse_params "$@"

  if [[ -z "$SELECTED_APPROACH" ]]; then
    msg "(entrypoint) No specific approach selected — running all available approaches."
    for ap in "${APPROACHES[@]}"; do
      run_approach "$ap" "$INSTANCE"
    done
  else
    run_approach "$SELECTED_APPROACH" "$INSTANCE"
  fi

  msg "[entrypoint] All tasks completed successfully."
}

run_approach() {
  local approach="$1"
  local instance="$2"
  local file="source/${approach}/run.py"

  msg "(entrypoint) Running ${approach} approach with instance=${instance}"

  if [[ -f "$file" ]]; then
    python3 "$file" "-n" "$instance"
  else
    msg "(entrypoint) File not found: $file — skipping ${approach} approach."
  fi
}

# =============================
# Entrypoint Execution
# =============================
main "$@"
