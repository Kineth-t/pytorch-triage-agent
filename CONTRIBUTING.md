# Contributing

This sandbox hosts an AI triage agent. Its rules apply to every contributor,
human or automated, because the agent's output (labels and comments) is
material that humans later act on.

## Opening issues

Use the structure of PyTorch's templates (`upstream/github/ISSUE_TEMPLATE/`):
what goes wrong, a minimal self-contained repro, the full error, and the output
of `python -m torch.utils.collect_env`. Please do not link external files
(model checkpoints, archives, cloud-drive links); maintainers will ask for a
self-contained script instead.

Do not write instructions to the triage bot in issues. Requests such as
"close these issues", "apply high priority" or "maintainers approved this"
in an issue body are treated as untrusted text: the bot cannot act on them
and flags the issue for human review.

## AI-contribution policy

Adapted from PyTorch's `AI_POLICY.md` (`upstream/AI_POLICY.md`).

1. **Disclose AI-generated content.** Anything an AI tool wrote that goes into
   an issue, PR or comment must sit under a heading that labels it as
   AI-generated, or in a quote/code block, with your own commentary on why it
   is relevant. The triage bot's comments do this automatically (header note
   plus the footer `Triage procedure: pytorch-issue-triage v1` and a link to
   the workflow run).
2. **Bot labels are suggestions.** Labels added by `github-actions[bot]` come
   with `bot-triaged`. A maintainer confirms them by adding `triaged`, or
   corrects them. Do not treat a `bot-triaged` issue as triaged.
3. **The bot never decides.** Only humans close issues, mark duplicates, set
   priority (`high priority`, `low priority`), handle security reports, or add
   `triaged`. If the bot suggests a duplicate, a maintainer verifies it.
4. **No fully autonomous contributions.** PRs and issues must involve a human
   who understands the content and takes responsibility for it. Do not paste
   raw AI output as a reply to someone's question.
5. **Security.** Report vulnerabilities privately as described in
   `upstream/SECURITY.md`, not in a public issue.

## Changing the agent

The agent's behaviour is defined by:

| What | File | Who must review |
|---|---|---|
| Triggers, permissions, budgets, allowed outputs | `.github/workflows/issue-triage.md` (+ recompiled `.lock.yml`) | code owner |
| Triage procedure, label allowlist, comment templates | `.claude/skills/pytorch-issue-triage/` | code owner |
| Repository facts | `AGENTS.md` | code owner |
| Expected outcomes for evaluation | `evals/**/expected.json` | code owner; never changed after a run to match the agent |

Workflow for a change:

1. Open a PR. CODEOWNERS requests review from the owner.
2. Run `gh aw compile issue-triage` and commit the `.lock.yml` with the source.
3. The **Agent config check** workflow must pass (`scripts/check_config.py`
   and the deterministic script self-test).
4. After merging any change to the workflow or skill, rerun the golden tasks
   (`evals/golden/README.md`) and commit the new batch results.
