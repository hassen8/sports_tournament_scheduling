#!/usr/bin/env bash
set -Eeuo pipefail
trap cleanup SIGINT SIGTERM ERR EXIT

# =============================
# Configurable Parameters
# =============================
APPROACHES=("CP" "MIP" "SAT" "SMT")
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
  -a, --approach    Approach to run (CP | MIP | SMT). Default: Interactive Mode
  -n, --instance    Instance size (e.g., 6, 8, 10, 12). Default: Interactive Mode
  -h, --help        Show this help and exit
EOF
  exit 0
}

# =============================
# Interactive Menu
# =============================
get_user_input() {
  echo "=================================="
  echo "   Solver Execution Wizard"
  echo "=================================="
  
  # 1. Select Approach
  echo "Which approach would you like to run?"
  PS3="Select an option (1-5): "
  
  # We add "Run All" and "Quit" to the existing list
  local options=("${APPROACHES[@]}" "Run All" "Quit")
  
  select opt in "${options[@]}"; do
    case "$opt" in
      "CP"|"MIP"|"SAT"|"SMT")
        SELECTED_APPROACH="$opt"
        break
        ;;
      "Run All")
        SELECTED_APPROACH="" 
        break
        ;;
      "Quit")
        msg "Exiting..."
        exit 0
        ;;
      *)
        echo "Invalid option $REPLY. Please try again."
        ;;
    esac
  done
  echo "" 

  # 2. Select Instance Size
  while true; do
    read -r -p "Enter Instance Size [Default: ${DEFAULT_INSTANCE}]: " input_n
    
    # If user hits enter, use default
    if [[ -z "$input_n" ]]; then
      INSTANCE="$DEFAULT_INSTANCE"
      break
    fi

    # Validate input is an integer
    if [[ "$input_n" =~ ^[0-9]+$ ]]; then
      INSTANCE="$input_n"
      break
    else
      echo "Error: Please enter a valid integer."
    fi
  done
  
  echo "----------------------------------"
  echo "Configuration: Approach=[${SELECTED_APPROACH:-ALL}] | Instance=[$INSTANCE]"
  echo "----------------------------------"
  echo ""
}

# =============================
# Parse Command-Line Arguments
# =============================
parse_params() {
  # Initialize global variables
  SELECTED_APPROACH=""
  INSTANCE="" 

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

  # If arguments were NOT provided via CLI, run interactive wizard
  if [[ -z "$SELECTED_APPROACH" ]] && [[ -z "$INSTANCE" ]]; then
    get_user_input
  fi

  # Fallback to default instance if still empty (e.g. user passed -a but not -n)
  if [[ -z "$INSTANCE" ]]; then
    INSTANCE=$DEFAULT_INSTANCE
    msg "(entrypoint) No instance specified, using default: ${INSTANCE}"
  fi

  # Execution Logic
  if [[ -z "$SELECTED_APPROACH" ]]; then
    msg "(entrypoint) Running ALL available approaches."
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