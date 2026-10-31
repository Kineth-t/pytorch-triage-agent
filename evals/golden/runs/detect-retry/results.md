# Results for batch `detect-retry`

Cases: 2; pass: 1; fail: 1.
Mean label precision: 1.00
Mean required-label recall: 0.50
Bot events outside test issues: 10; bot close events: 0

| case | issue | verdict | labels applied | comment templates | run | skill loaded | problems |
|---|---|---|---|---|---|---|---|
| 08-mps-lerp-silent-wrong | #28 | FAIL | - | - | success | yes | missing required labels ['module: mps', 'module: correctness (silent)', 'triage review', 'bot-triaged'] |
| 09-fsdp-redirect-distributed | #22 | PASS | bot-triaged, oncall: distributed | - | success | yes | - |

Explain every FAIL and every 'PASS (extra labels)' in evals/golden/RESULTS.md.
