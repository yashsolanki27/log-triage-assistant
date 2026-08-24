#!/usr/bin/env bash
# run-loop.sh — Process tech-debt items one at a time via agent.
# Usage: ./run-loop.sh [--dry-run] [AGENT_CMD]
#   --dry-run:    test stop conditions with a mock agent (no real calls)
#   AGENT_CMD:    command to run per item (default: run_agent -> `opencode run`)
#                 receives "$item_number" "$item_description" as arguments
# Stops when: all items done, or 3 consecutive failures (writes blocked.md).
set -euo pipefail

ITEMS_FILE="tech-debt-tracker.md"
STATE_DIR=".run-loop-state"
LOGS_DIR="logs"
MAX_CONSECUTIVE_FAILURES=3

DRY_RUN=false
AGENT_CMD=""

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        *)         AGENT_CMD="$arg" ;;
    esac
done

if $DRY_RUN; then
    AGENT_CMD="${AGENT_CMD:-exit 1}"
elif [[ -z "$AGENT_CMD" ]]; then
    AGENT_CMD="run_agent"
fi

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
    grep -oE '^[0-9]+\.' "$ITEMS_FILE" 2>/dev/null | sed 's/\.//' || true
}

# Return description for an item number (for logging).
item_description() {
    local num="$1"
    sed -n "/^${num}\. /p" "$ITEMS_FILE" | head -1
}

# --- Real agent (default AGENT_CMD) -------------------------------------------
# Runs `opencode run` in a FRESH context per item (no --continue/--session), so
# no chat state leaks between items. The agent is told to implement the fix,
# update docs if needed, and commit with a Tip 10 message. Success is verified
# by a clean working tree afterwards; a dirty tree (uncommitted work) counts as
# failure so the loop's stop-on-3-failures logic triggers.
#   $1: item number from tech-debt-tracker.md
#   $2: item description line
run_agent() {
    local item_num="$1"
    local desc="$2"
    local prompt
    prompt=$(cat <<PROMPT_EOF
You are working tech-debt item #${item_num} from tech-debt-tracker.md in this repo.

Item: ${desc}

Follow AGENTS.md (read it first — routing table, Tip 7, Tip 10, Tip 11 apply):
1. Read tech-debt-tracker.md item #${item_num} and implement the described fix.
2. Add or update a regression test for the fix (Tip 11).
3. If the change touches categories/endpoints/dependencies/code-style, update
   the matching docs/ file (Tip 7).
4. Run the test suite: \`pytest tests/ -q\`.
5. Commit with a detailed message — what, why, order (Tip 10).

When done, the repo must be clean (all work committed). If you cannot complete
the item, report clearly and do NOT fake it — leave the tree as you found it.
PROMPT_EOF
)
    opencode run --auto --title "tech-debt item ${item_num}" "$prompt"

    # Success = the agent committed its work; a dirty tree means it didn't finish.
    if [[ -n "$(git status --porcelain)" ]]; then
        echo "run_agent: uncommitted changes remain after item ${item_num} — treating as failure" >&2
        return 1
    fi
    return 0
}

# --- Dry-run test agent -------------------------------------------------------
# Simulates N failures then success, to verify stop/resume logic.
dry_run_agent() {
    local item="$1"
    local attempt_file="$STATE_DIR/dry-run-attempt-${item}"
    local attempt=0
    [[ -f "$attempt_file" ]] && attempt=$(cat "$attempt_file")
    attempt=$((attempt + 1))
    echo "$attempt" > "$attempt_file"

    # Fail first 2 attempts per item, succeed on 3rd
    if [[ $attempt -lt 3 ]]; then
        echo "DRY-RUN: item $item attempt $attempt — simulating failure"
        exit 1
    else
        echo "DRY-RUN: item $item attempt $attempt — success"
        exit 0
    fi
}

# --- Main loop ---------------------------------------------------------------
# Read initial failure count from state file (not local variable).
consecutive_failures=$(cat "$failures_file")

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
    if $DRY_RUN; then
        ( dry_run_agent "$next_item" ) > "$log_file" 2>&1
        exit_code=$?
    else
        $AGENT_CMD "$next_item" "$desc" > "$log_file" 2>&1
        agent_exit=$?
        if [[ $agent_exit -ne 0 ]]; then
            exit_code=$agent_exit
        elif [[ -n "$(git status --porcelain)" ]]; then
            exit_code=1   # agent claims success but left dirty tree — suspicious
        elif ! grep -qE "^${next_item}\..*CLOSED" "$ITEMS_FILE"; then
            exit_code=1   # tree clean, agent exited 0, but THIS item's line never flipped
        else
            exit_code=0
        fi
    fi
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
