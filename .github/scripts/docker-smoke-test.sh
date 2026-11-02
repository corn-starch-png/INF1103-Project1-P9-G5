#!/bin/bash
set -e

output=$(timeout --signal=INT 3s docker compose -f .github/workflows/docker-compose.ci.yml \
run --rm -T test < .github/workflows/docker_input.txt 2>&1 || true)
#timeout will send interupt signal afer 3 second, || true ensures rest of this script runs if docker test fails
echo "$output" #prints outpout of test to terminal 

if echo "$output" | grep -Fq 'Household summary:' \
   && echo "$output" | grep -Fq '  1. Rick, 70, Male, diet: none' \
   && echo "$output" | grep -Fq '  2. Morty, 15, Male, diet: none'; then
  echo "Smoke test passed: household summary printed." #successful if execution returns exit 0 by defualt
else
echo "Smoke test failed: expected prompt not reached."
exit 1
fi