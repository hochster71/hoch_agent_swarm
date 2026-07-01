#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# scripts/security/rc22_rollback.sh — Operator Release Rollback Orchestrator

set -euo pipefail

# Color formatting
GREEN="\033[92m"
RED="\033[91m"
YELLOW="\033[93m"
CYAN="\033[96m"
BOLD="\033[1m"
RESET="\033[0m"

print_help() {
    echo -e "${BOLD}Usage:${RESET} $0 [tag_or_commit]"
    echo -e "  Rolls back the local repository working directory to a specified release tag or commit SHA."
    echo -e ""
    echo -e "${BOLD}Options:${RESET}"
    echo -e "  --help    Show this help message"
}

if [[ $# -eq 0 ]] || [[ "$1" == "--help" ]]; then
    print_help
    exit 0
fi

TARGET="$1"

echo -e "${CYAN}${BOLD}========================================================================${RESET}"
echo -e "${CYAN}${BOLD}                 RELEASE ROLLBACK ORCHESTRATOR (rc22)                   ${RESET}"
echo -e "${CYAN}${BOLD}========================================================================${RESET}"

# 1. Verify target exists in git history
echo -e "Checking if target ${BOLD}${TARGET}${RESET} exists..."
if ! git rev-parse --verify "$TARGET" >/dev/null 2>&1; then
    echo -e "  [${RED}ERROR${RESET}] Target '${TARGET}' not found in local git database."
    echo -e "  Please verify the tag name or commit hash and try again."
    exit 1
fi
echo -e "  [${GREEN}OK${RESET}] Target exists."

# 2. Check if working tree is clean
echo -e "\nChecking git working tree status..."
DIRTY_COUNT=$(git status --porcelain | wc -l | tr -d ' ')
if [[ "$DIRTY_COUNT" -ne 0 ]]; then
    echo -e "  [${YELLOW}WARNING${RESET}] Working tree has uncommitted changes."
    git status --short
    echo -e ""
    echo -e "${RED}${BOLD}CAUTION:${RESET} Hard rollback will discard all uncommitted changes!"
fi

# 3. Print diff preview
echo -e "\n${BOLD}File changes summary between HEAD and target:${RESET}"
git diff --stat HEAD "$TARGET" || echo "No changes detected."

# 4. Prompt operator for confirmation
echo -e "\n${YELLOW}${BOLD}WARNING: You are about to roll back to target: ${TARGET}${RESET}"
read -rp "Are you sure you want to proceed? (yes/No): " CONFIRM
if [[ "$CONFIRM" != "yes" ]]; then
    echo -e "Rollback aborted by operator."
    exit 0
fi

# 5. Execute rollback
echo -e "\nExecuting rollback..."
# We run git checkout to safely move to the target commit/tag
if git checkout "$TARGET"; then
    echo -e "  [${GREEN}SUCCESS${RESET}] Local codebase rolled back to ${BOLD}${TARGET}${RESET}."
    echo -e "\n${GREEN}${BOLD}Rollback verified successfully.${RESET}"
    echo -e "Remember to restart uvicorn server on port 8000 to reload updated modules."
else
    echo -e "  [${RED}FAIL${RESET}] Rollback command failed."
    exit 1
fi
