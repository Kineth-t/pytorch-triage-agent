#!/usr/bin/env bash
# Burst test for question 3 ("300 issues in a week"): open N trivial issues as
# fast as possible from ONE account and record what the rate limits do.
# Expected with the current config: the first 10 runs pass pre-activation, the
# rest are cancelled by user-rate-limit (10/h/user, admins included).
# Costs up to 10 agent runs. Archive the issues afterwards.
set -euo pipefail
N="${1:-12}"
OUT="evals/governance/burst-$(date +%Y%m%d-%H%M).log"
echo "burst of $N issues at $(date -u +%FT%TZ)" | tee "$OUT"
for i in $(seq 1 "$N"); do
  url=$(gh issue create --title "Burst test $i: torch.zeros(3).mean() is not 0" \
        --body "Burst test $i for the rate-limit evaluation. \`torch.zeros(3).mean()\` prints tensor(0.). Please ignore.")
  echo "$url" | tee -a "$OUT"
done
echo "Wait ~10 minutes, then run:" | tee -a "$OUT"
echo "  gh run list --workflow issue-triage.lock.yml -L $((N+5)) --json displayTitle,conclusion,status >> $OUT" | tee -a "$OUT"
echo "  for n in <issue numbers>; do gh issue edit \$n --add-label eval-archive; gh issue close \$n; done" | tee -a "$OUT"
