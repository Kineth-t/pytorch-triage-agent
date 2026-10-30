# Results for batch `b2`

Cases: 7; pass: 3; fail: 4.
Mean label precision: 0.88
Mean required-label recall: 0.60
Bot events outside test issues: 2; bot close events: 0

| case | issue | verdict | labels applied | comment templates | run | skill loaded | problems |
|---|---|---|---|---|---|---|---|
| 01-question-reopen-pr | #16 | FAIL | - | request_more_info | success | yes | missing required labels ['better-on-discuss-forum', 'bot-triaged']; comment templates ['request_more_info'] != expected ['redirect_to_forum'] (alternatives []) |
| 02-docs-feedback-no-info | #18 | FAIL | bot-triaged | - | success | yes | missing required labels ['module: docs']; comment templates [] != expected ['request_more_info'] (alternatives []) |
| 05-mps-unpool-input-checks | #19 | PASS | bot-triaged, module: error checking, module: mps | - | success | yes | - |
| 06-dataloader-prefetch-zero | #20 | PASS | bot-triaged, module: dataloader, module: error checking | - | success | yes | - |
| 07-typing-stub | #21 | PASS (extra labels) | bot-triaged, function request, module: loss, module: typing | - | success | yes | - |
| 09-fsdp-redirect-distributed | #22 | FAIL | - | - | success | yes | missing required labels ['oncall: distributed', 'bot-triaged'] |
| 10-pt2-cond-symint | #26 | FAIL | bot-triaged, module: compile ux, oncall: pt2 | - | success | yes | missing required labels ['module: higher order operators'] |

Explain every FAIL and every 'PASS (extra labels)' in evals/golden/RESULTS.md.
