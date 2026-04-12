#!/usr/bin/env bash
set -uo pipefail

# Runs every test-*.sh under ~/.claude/hooks/tests/ and reports suite-level
# pass/fail counts. Exits non-zero if any suite fails.

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

SUITES_PASSED=0
SUITES_FAILED=0
FAILED_NAMES=()

printf "${BOLD}${CYAN}═══════════════════════════════════════════════════${NC}\n"
printf "${BOLD}${CYAN}  Claude Hooks Test Suite Runner${NC}\n"
printf "${BOLD}${CYAN}═══════════════════════════════════════════════════${NC}\n"

for test_file in "$TESTS_DIR"/test-*.sh; do
  [ -f "$test_file" ] || continue
  name=$(basename "$test_file" .sh)
  printf "\n${BOLD}━━━ %s ━━━${NC}\n" "$name"
  if bash "$test_file"; then
    SUITES_PASSED=$((SUITES_PASSED+1))
    printf "${GREEN}  SUITE PASSED${NC}\n"
  else
    SUITES_FAILED=$((SUITES_FAILED+1))
    FAILED_NAMES+=("$name")
    printf "${RED}  SUITE FAILED${NC}\n"
  fi
done

printf "\n${BOLD}${CYAN}═══════════════════════════════════════════════════${NC}\n"
printf "${BOLD}Summary${NC}\n"
printf "  Suites passed: ${GREEN}%d${NC}\n" "$SUITES_PASSED"
printf "  Suites failed: ${RED}%d${NC}\n" "$SUITES_FAILED"
if [ "$SUITES_FAILED" -gt 0 ]; then
  printf "\n${RED}Failed suites:${NC}\n"
  for n in "${FAILED_NAMES[@]}"; do
    printf "  - %s\n" "$n"
  done
  exit 1
fi
printf "${GREEN}${BOLD}  ALL SUITES PASSED${NC}\n"
exit 0
