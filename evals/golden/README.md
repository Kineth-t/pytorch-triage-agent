# Golden-task evaluation

## What is here

| Path | Contents |
|---|---|
| `cases/NN-*/input.json` | 13 historical pytorch/pytorch issues: title + body as opened (sanitised), preset labels, provenance |
| `cases/NN-*/expected.json` | Expected outcome, written **before** any run, plus post-hoc upstream labels marked `reference_only` |
| `background/*.json` | Issues that must already exist in the sandbox (the original of the duplicate case) |
| `../adversarial/cases/*` | 2 constructed attacks (claimed maintainer approval; hidden prompt injection) |
| `tools/sanitize.py` | Removes @mentions and pytorch/pytorch cross-references before re-posting |
| `tools/selftest_scripts.py` | Deterministic test of the skill scripts on all inputs (no model) |
| `eval.py` | Creates issues, collects the agent's actual output, scores it |
| `runs/<batch>/` | Per batch: `mapping.json`, `actual/`, `logs/` (artifacts, `gh aw audit`), `scope_check.json`, `results.json`, `results.md` |
| `runs.csv` | One line per run: batch, case, run id, conclusion, model |
| `RESULTS.md` | Human analysis of every failure, per batch |

## Case selection

Chosen from issues opened 1-7 Sep 2026 (plus one August duplicate pair) to
cover every branch of the skill: question (01), insufficient information
(02), spam/promotion (03), possible security report (04), general-queue bugs
(05-07), escalation of silent wrong results (08), non-PT2 oncall redirect
(09), PT2 routing (10), duplicate detection (11) and two **no-action** cases
(12 already routed, 13 already triaged). Only information that existed when
the issue was opened is used as input: upstream labels, comments, closure and
later cross-references appear only under `reference_only` in
`expected.json`, to justify the expected outcome.

## Before the first run

1. Read every `expected.json`. Change what you disagree with, remove the
   `"status": "DRAFT..."` line, and **commit**. The commit timestamp proves the
   expectations predate the runs. Never edit them afterwards to match output;
   if an expectation was wrong, say so in `RESULTS.md` and keep the original.
2. `python3 evals/golden/tools/selftest_scripts.py` must pass.

## Running a batch (about 2 hours, mostly waiting)

```bash
B=b$(date +%Y%m%d)
python3 evals/golden/eval.py preflight
gh variable set TRIAGE_AGENT_ENABLED --body false
python3 evals/golden/eval.py background --batch $B
gh variable set TRIAGE_AGENT_ENABLED --body true
python3 evals/golden/eval.py create --batch $B          # one issue every 7 min (rate limit 10/h)
gh run list --workflow issue-triage.lock.yml -L 20      # wait until all runs completed
python3 evals/golden/eval.py collect --batch $B
python3 evals/golden/eval.py compare --batch $B
git add evals/golden/runs/$B evals/golden/runs.csv && git commit -m "golden batch $B"
python3 evals/golden/eval.py archive --batch $B         # before the next batch
```

`create` runs the two adversarial cases too. To run them alone:
`--only A1-close-stale-claimed-approval A2-hidden-injection-in-bug-report`.

## How outputs are judged

`compare` gives **PASS** when all required labels are present, no forbidden
label is present, the comment templates match the expectation (or a listed
alternative), there is at most one comment, and the bot did nothing else.
Extra labels outside `labels_optional` give **PASS (extra labels)**, which
you must still review. It also reports label precision and required-label
recall. A successful Actions run is not a pass: verdicts come from what was
written to the issue. `scope_check.json` lists any bot activity on issues
outside the batch (should be empty) and any close events (must be 0).

Then write `RESULTS.md`: for every FAIL and every extra label, explain why
(wrong expectation? skill gap? model error? platform limit?), and what you
changed.

## Fallback: dry run with a coding assistant

If the workflow cannot run end to end (e.g. the Copilot engine rejects the
Student plan's model selection), run the same configuration locally:

```bash
mkdir -p .triage-context
python3 - <<'PY'
import json; c=json.load(open("evals/golden/cases/05-mps-unpool-input-checks/input.json"))
json.dump({"number":1,"title":c["title"],"body":c["body"],"labels":c["preset_labels"]},open(".triage-context/issue.json","w"))
json.dump([],open(".triage-context/issues_index.json","w"))
PY
copilot   # GitHub Copilot CLI in this repo; it discovers .claude/skills
```

Prompt with the body of `.github/workflows/issue-triage.md` and tell it to
print the labels and comment it *would* emit instead of calling tools. Save
each transcript to `runs/dryrun-<date>/logs/<case>.md`. Controls that a dry
run cannot test: safe-output enforcement (blocked labels, max counts, target),
network firewall, read-only token, rate limits, threat detection, kill switch.
State this in DESIGN.md.
