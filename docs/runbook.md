# Operations runbook

Owner and accountable person: **Kenneth Tay (@Kineth-t)**, repository admin.

## Kill switch

Three independent levels, fastest first. All work from a phone browser
(github.com in Safari/Chrome; the GitHub Mobile app cannot edit Actions
variables or disable workflows, so use the browser, "Desktop site" if a
menu is hidden).

| Level | Effect | Phone steps |
|---|---|---|
| 1. Variable | New runs skip the agent job (`if: vars.TRIAGE_AGENT_ENABLED == 'true'`). Takes effect for the next trigger. | Repo -> Settings -> Secrets and variables -> Actions -> Variables -> `TRIAGE_AGENT_ENABLED` -> edit -> `false` -> Update |
| 2. Disable workflow | GitHub stops scheduling the workflow at all. | Repo -> Actions -> "First-pass issue triage" -> `...` menu -> Disable workflow |
| 3. Revoke token | Even a running or re-enabled agent cannot call the model. | Profile -> Settings -> Developer settings -> Fine-grained tokens -> the Copilot token -> Revoke (or delete secret `COPILOT_GITHUB_TOKEN` in repo settings) |

**Runs already executing**: Actions -> the run (`Triage #<n>`) -> Cancel
workflow. Writes happen only in the later `safe_outputs` job, after the agent
and threat-detection jobs; cancelling before `safe_outputs` starts means no
label or comment is written. If labels/comments were already written, remove
them by hand; nothing the agent can do is irreversible (no close, delete,
merge or push).

Laptop equivalents: `gh variable set TRIAGE_AGENT_ENABLED --body false`,
`gh aw disable issue-triage`, `gh run cancel <id>`.

Automatic stop: `stop-after: 2026-12-31` in the workflow disables triggers
on that date until someone recompiles with a new date.

## Budgets

| Budget | Value | Where |
|---|---|---|
| Runs per user | 10 per 60 min; admins are exempt (the compiler drops `ignored-roles: []`), untested | `user-rate-limit` |
| Agent runtime | 8 min agentic step; 60 min agent job; 10 min detection | `timeout-minutes`, compiler defaults |
| Model turns | 30 per run | `max-turns` |
| AI credits | 150 per run, 1,500 per rolling 24 h for this workflow | `max-ai-credits`, `max-daily-ai-credits` |
| Outputs | 1 `add_labels` call (<= 6 labels), 1 comment, per run | `safe-outputs` |
| Money | $0: Student allowance only, no paid overage; public repo, free Actions minutes | GitHub billing settings |
| Lifetime | triggers stop 2026-12-31 | `stop-after` |

## Audit trail

| Record | Where | Retention |
|---|---|---|
| Trigger, actor, run per issue | Actions run named `Triage #<n>` | 90 days (public repo default) |
| Model, tokens, AI credits, tool calls | `gh aw audit <run-id>`, `gh aw logs` | while run logs exist |
| Prompt, agent transcript, safe-output JSON, `skill_inventory.json`, threat-detection verdict | run artifacts (`gh run download <id>`) | artifact retention |
| What was written | issue timeline (actor `github-actions[bot]`), comment footer links to the run | permanent |
| Configuration at the time | git history of `.github/workflows/issue-triage.*` and `.claude/` | permanent |
| Evaluation evidence | `evals/golden/runs/<batch>/` (committed) | permanent |

## Drift detection

The model is not pinned (Student plan: automatic model selection only), so
the provider can change it without notice.

- **When**: after any change to the workflow or skill; after any gh-aw
  upgrade (`gh aw upgrade`); when `gh aw audit` shows a model name different
  from the last batch; and at least every two weeks while the agent is on.
- **How**: `evals/golden/README.md`, a new batch `bYYYYMMDD`. Cost: 15 runs.
- **Who reviews**: the owner reads `results.md` and every FAIL, compares
  model names in `runs.csv`, and records the verdict in `evals/golden/RESULTS.md`.
  Any new FAIL on a previously passing case -> kill switch level 1 until explained.
- **Continuous signal**: humans correcting bot labels. Search
  `is:issue label:bot-triaged -label:triaged` (unconfirmed suggestions) and
  look at timeline "removed label" events by humans.

## Accountability

- Can change or disable the configuration: repository admins (only
  @Kineth-t). CODEOWNERS and the **Agent config check** are in place, but
  the `main` ruleset that would require a reviewed PR (docs/setup.md §6) is
  not enabled: with a sole maintainer nobody can approve, so changes were
  pushed directly to `main`.
- Responsible for the agent's actions: the owner of the repository and of the
  `COPILOT_GITHUB_TOKEN` (@Kineth-t). Model usage is billed to that account.
- Actions are attributed to `github-actions[bot]`, never to a personal
  account; each comment links to its run.
