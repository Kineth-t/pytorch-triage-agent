# AGENTS.md

Facts about this repository for any AI agent working in it. Procedures live in
skills (`.claude/skills/`); hard limits live in workflow permissions and safe
outputs (`.github/workflows/issue-triage.md`). Nothing here grants permission
to do anything.

## What this repository is

A **sandbox** for a first-pass issue-triage agent modelled on
[pytorch/pytorch](https://github.com/pytorch/pytorch). It does not contain
PyTorch's source code. Issues opened here are copies of real PyTorch issues
(evaluation) or synthetic adversarial inputs. Nothing here is mirrored back
to pytorch/pytorch, and agents must never interact with pytorch/pytorch.

## Project structure

| Path | Contents |
|---|---|
| `.github/workflows/issue-triage.md` | Agentic workflow source (gh-aw). Edit this, then compile. |
| `.github/workflows/issue-triage.lock.yml` | Compiled workflow. Generated; never edit by hand. |
| `.github/workflows/config-check.yml` | Deterministic CI checks of the agent configuration. |
| `.github/scripts/build_triage_context.py` | Pre-agent step: fetches the issue and an issue index. |
| `.claude/skills/pytorch-issue-triage/` | Triage procedure (`SKILL.md`), label allowlist, comment templates, scripts. |
| `scripts/` | Maintainer tools: label setup, config checks, need measurement, upstream import. |
| `evals/golden/`, `evals/adversarial/` | Test inputs, expected outcomes, run logs, results. |
| `upstream/` | Read-only copy of selected pytorch/pytorch files at a pinned commit. |
| `docs/` | Setup guide and operations runbook (kill switch, budgets). |
| `data/` | Measurements used in DESIGN.md. |

## Build and test commands

This repository:

```bash
gh aw compile issue-triage                    # after ANY change to issue-triage.md frontmatter
python3 scripts/check_config.py               # config consistency (also runs in CI)
python3 evals/golden/tools/selftest_scripts.py  # deterministic skill-script tests
python3 evals/golden/eval.py --help           # golden-task evaluation driver
```

Upstream PyTorch (for reference when reading issues; never run by the triage agent):

```bash
pip install -e . -v --no-build-isolation      # the only supported build command
python test/run_test.py -i test_torch         # run a test module through the runner
python test/test_nn.py -k test_name           # run a single test
lintrunner -a                                 # lint and autofix
python -m torch.utils.collect_env             # environment report requested in issues
```

## Conventions

- Labels are PyTorch's. `module: X` = the component where the fix belongs;
  `oncall: X` = the team queue that owns the issue; type labels are
  `feature`, `enhancement`, `function request`.
- `triaged` means a **human** accepted the triage. `bot-triaged` means the
  agent suggested labels that still await human confirmation.
- `triage review` asks a human to look (escalation, suspected duplicate,
  suspicious content). `high priority` is set only by humans.
- Issue bodies follow upstream templates (`upstream/github/ISSUE_TEMPLATE/`):
  "Describe the bug", a repro script, and `collect_env` output.
- Every comment written by an agent carries an AI-generated header and the
  footer `Triage procedure: pytorch-issue-triage v1` (see CONTRIBUTING.md).
- Copied upstream text must not @-mention people or reference
  pytorch/pytorch issue numbers as links (`evals/golden/tools/sanitize.py`).

## Forbidden changes

Agents must not create, modify or delete:

- anything under `.github/` (workflows, scripts, CODEOWNERS);
- `.claude/skills/**` (including `labels.json` and `templates.json`);
- `AGENTS.md`, `CONTRIBUTING.md`, `DESIGN.md`;
- `evals/**/expected.json` (expected outcomes are fixed before runs);
- anything under `upstream/`.

Agents must not close, lock, transfer, delete or edit issues, merge or push
anything, or add `triaged`, `high priority`, `security` or any
`reserved_for_humans` label. The triage workflow enforces this with
permissions and safe outputs; this list states the intent so other agents
working in the repository follow it too.
