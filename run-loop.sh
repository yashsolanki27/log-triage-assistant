#!/usr/bin/env bash
# run-loop.sh — Process tech-debt items one at a time via agent.
# Usage: ./run-loop.sh [AGENT_CMD]
#   AGENT_CMD: command to run per item (default: "echo TODO: implement agent")
# Stops when: all items done, or 3 consecutive failures (writes blocked.md).
set -euo pipefail

ITEMS_FILE="tech-debt-tracker.md"
STATE_DIR=".run-loop-state"
LOGS_DIR="logs"
MAX_CONSECUTIVE_FAILURES=3

AGENT_CMD="${1:-echo TODO: implement agent for item}"

mkdir -p "$STATE_DIR" "$LOGS_DIR"

# --- State helpers -----------------------------------------------------------
iteration_file="$STATE_DIR/iteration"
failures_file="$STATE_DIR/consecutive_failures"
done_file="$STATE_DIR/done"

[[ -f "$iteration_file" ]]   || echo 0 > "$iteration_file"
[[ -f "$failures_file" ]]    || echo 0 > "$failures_file"
[[ -f "$done_file" ]]        || touch "$done_file"

next_iteration() {
    local n
    n=$(cat "$iteration_file")
    echo $((n + 1)) > "$iteration_file"
    echo $((n + 1))
}

reset_failures() { echo 0 > "$failures_file"; }

bump_failures() {
    local n
    n=$(cat "$failures_file")
    echo $((n + 1)) > "$failures_file"
    echo $((n + 1))
}

mark_done() {
    local item_num="$1"
    echo "$item_num" >> "$done_file"
}

is_done() {
    local item_num="$1"
    grep -qx "$item_num" "$done_file" 2>/dev/null
}

# --- Item parsing -------------------------------------------------------------
# Items in tech-debt-tracker.md look like:
#   1. **Title** — description
# Extract the leading number from each such line.
parse_items() {
    grep -oE '^[0-9]+\.' "$ITEMS_FILE" | sed 's/\.//'
}

# Return description for an item number (for logging).
item_description() {
    local num="$1"
    sed -n "/^${num}\. /p" "$ITEMS_FILE" | head -1
}

# --- Main loop ---------------------------------------------------------------
consecutive_failures=0

while true; do
    # Find next unfinished item
    next_item=""
    for item_num in $(parse_items); do
        if ! is_done "$item_num"; then
            next_item="$item_num"
            break
        fi
    done

    if [[ -z "$next_item" ]]; then
        echo "All items done."
        exit 0
    fi

    iter=$(next_iteration)
    desc=$(item_description "$next_item")
    log_file="${LOGS_DIR}/iteration-${iter}.log"

    echo "=== Iteration $iter: item $next_item ==="
    echo "Item: $desc"
    echo "Log:  $log_file"

    # Run agent, capture output and exit code
    set +e
    $AGENT_CMD "$next_item" "$desc" > "$log_file" 2>&1
    exit_code=$?
    set -e

    echo "Exit code: $exit_code" | tee -a "$log_file"

    if [[ $exit_code -eq 0 ]]; then
        mark_done "$next_item"
        reset_failures
        consecutive_failures=0
        echo "Item $next_item completed."
    else
        consecutive_failures=$(bump_failures)
        echo "Item $next_item failed (consecutive failures: $consecutive_failures)."

        if [[ $consecutive_failures -ge $MAX_CONSECUTIVE_FAILURES ]]; then
            reason="Stopped after $MAX_CONSECUTIVE_FAILURES consecutive failures. Last item: $next_item (exit $exit_code)."
            echo "$reason" > blocked.md
            echo "BLOCKED: $reason"
            exit 1
        fi
    fi

    echo ""
done
