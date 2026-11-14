#!/bin/bash
set -e

output=$(timeout --signal=INT 3s docker compose -f .github/smoke_test/docker-compose.ci.yml \
run --rm -T -e USE_MONGO=0 test< /dev/null 2>&1 || true)
# [STATUS] NEW MODIFY
#__ The new startup fixture explicitly creates an offline household before profiles.
#timeout will send interupt signal afer 3 second, || true ensures rest of this script runs if docker test fails
echo "$output" #prints outpout of test to terminal 

if echo "$output" | grep -Fq 'Welcome to the QuantiFresh!' \
   && echo "$output" | grep -Fq 'Choose your Household Space:' \
   && echo "$output" | grep -Fq '1. Enter Household Space ID' \
   && echo "$output" | grep -Fq '2. Create Household Space' \
   && echo "$output" | grep -Fq '3. Exit the program'; then
  echo "Smoke test passed: menu displayed." #successful if execution returns exit 0 by defualt
else
echo "Smoke test failed: menu not displayed"
exit 1
fi
