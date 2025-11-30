#!/usr/bin/env bash
set -Eeuo pipefail
trap cleanup SIGINT SIGTERM ERR EXIT

APPROACHES=("CP" "MIP" "SAT" "SMT")
DEFAULT_INSTANCE=6

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
  -a, --approach    Approach to run (CP | MIP | SAT | SMT)
  -n, --instance    Instance size (6, 8, 10, 12, ...)
  -h, --help        Show this help message

Examples:
  ./entrypoint.sh --approach CP --instance 8
  ./entrypoint.sh
EOF
  exit 0
}

parse_params() {
  SELECTED_APPROACH=""
  INSTANCE=$DEFAULT_INSTANCE

  if [[ $# -gt 0 && "$1" != -* ]]; then
    SELECTED_APPROACH="$1"
    if [[ $# -gt 1 ]]; then
      INSTANCE="$2"
    fi
    return
  fi

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

main() {
  parse_params "$@"

  if [[ -z "$SELECTED_APPROACH" ]]; then
    msg "(entrypoint) Running ALL approaches..."
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

  msg "(entrypoint) Running ${approach} with instance=${instance}"

  case "$approach" in
    CP)
      python3 source/CP/run.py -n "$instance"
      ;;
    
    MIP)
      python3 source/MIP/run.py -n "$instance"
      ;;
    
    SAT)
      python3 source/SAT/run.py --mode all -n "$instance"
      ;;
    
    SMT)
      python3 source/SMT/run.py --mode all -n "$instance"
      ;;
    
    *)
      msg "(entrypoint) Unknown approach: ${approach}"
      ;;
  esac
}

main "$@"
