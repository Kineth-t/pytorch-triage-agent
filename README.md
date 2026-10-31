# PyTorch issue-triage agent (sandbox)

A GitHub Agentic Workflow (gh-aw, Copilot engine) that does first-pass triage
of new issues in a sandbox modelled on [pytorch/pytorch](https://github.com/pytorch/pytorch):
it suggests routing labels, flags duplicates and urgent reports for humans,
and posts at most one templated comment. It cannot close, edit, assign,
merge or push. Design and governance: [DESIGN.md](DESIGN.md). Evaluation
results and failure analysis: [evals/golden/RESULTS.md](evals/golden/RESULTS.md).

## Layout

```
.github/workflows/issue-triage.md         agentic workflow (source)
.github/workflows/issue-triage.lock.yml   compiled workflow (gh aw compile)
.github/workflows/config-check.yml        deterministic CI checks of the config
.github/scripts/build_triage_context.py   pre-agent step (fetches issue + index)
.github/aw/actions-lock.json              pinned action SHAs used by the compiler
.github/CODEOWNERS
.claude/skills/pytorch-issue-triage/      SKILL.md, labels.json, templates.json, scripts/
AGENTS.md  CONTRIBUTING.md  DESIGN.md
docs/setup.md      step-by-step setup (zero cost)
docs/runbook.md    kill switch, budgets, audit trail, drift, accountability
docs/evidence/     screenshots: billing, Copilot settings, kill-switch test
evals/golden/      13 historical cases, expected outcomes, eval driver,
                   RESULTS.md, runs/ (per-batch logs and artifacts), runs.csv
evals/adversarial/ 2 attack cases
evals/governance/  burst test
scripts/           label setup, config check, need measurement, upstream import
upstream/          pytorch/pytorch files at a pinned commit (reference only)
data/              measurements used in DESIGN.md
```

## Quick start

See [docs/setup.md](docs/setup.md), then [evals/golden/README.md](evals/golden/README.md).

```bash
gh aw compile issue-triage && python3 scripts/check_config.py
python3 evals/golden/tools/selftest_scripts.py
```

## Before submitting (owner checklist)

- [x] Review and edit every `expected.json`; remove the `DRAFT` status; commit before the first run (`6edb72e`).
- [x] `scripts/measure_need.py` for Sep 2026 and Sep 2025; put the numbers in DESIGN.md §1.
- [x] Smoke test; confirm skill loading (`skill_inventory.json`, `TRIAGE-SUMMARY` line).
- [x] Run golden batches (b1, b2, b3); collect; compare; explain every failure in `evals/golden/RESULTS.md`.
- [x] Run A1 and A2; record what was attempted, rejected and written.
- [x] Kill-switch test from a phone; screenshots in `docs/evidence/`. The burst test was not run
      (admins are exempt from the compiled rate limit; see `evals/golden/RESULTS.md`).
- [ ] Replace every ⟨TODO⟩ in DESIGN.md; rewrite the AI-use statement yourself; keep ≤150 lines.
- [ ] Submit the link to the exact commit (public repo, or add `ctreude` as collaborator).
