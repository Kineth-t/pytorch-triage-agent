# Setup (zero cost: public repo + Copilot Student)

Commands assume macOS with Homebrew and that this repository is your local
checkout. Replace `Kineth-t/pytorch-triage-agent` if you use another name.

## 1. Accounts and cost guards

1. Confirm **GitHub Copilot Student** is active: github.com/settings/copilot.
2. Settings -> Billing and licensing: make sure no paid budget / additional
   usage is enabled for Copilot. Screenshot this page into `docs/evidence/`
   (it is the evidence for the "Budgets" control).
3. Keep the repository **public**: GitHub Actions minutes are free for
   public repositories.

## 2. Tools

```bash
brew install gh python@3.12
gh auth login                       # HTTPS, browser login
gh extension install github/gh-aw
gh aw version                       # this repo was compiled with v0.93.5
```

## 3. Create the sandbox repository

```bash
gh repo create Kineth-t/pytorch-triage-agent --public --source . --push
```

## 4. Labels (this is part of the safety design)

```bash
python3 scripts/setup_sandbox_labels.py                    # dry run
python3 scripts/setup_sandbox_labels.py --apply --prune    # create allowlist, delete GitHub's defaults
```

`--prune` deletes labels such as `bug` and `question` that are not in the
allowlist. The agent cannot create labels, so the repository's label set is
its effective allowlist.

## 5. Copilot token and switches

1. Create a fine-grained personal access token: Settings -> Developer
   settings -> Fine-grained tokens -> Generate. Resource owner: your account.
   Expiration: 60 days. Repository access: *Public repositories* (no
   repository permissions). Account permissions -> **Copilot Requests**
   (the only permission it needs; it lets the token spend your Copilot
   allowance and nothing else).
2. Store it and set the kill-switch variable:

```bash
gh secret set COPILOT_GITHUB_TOKEN          # paste the token
gh variable set TRIAGE_AGENT_ENABLED --body false   # stays off until you test
```

## 6. Branch protection (human approval for config changes)

Settings -> Rules -> Rulesets -> New branch ruleset on `main`:
require a pull request before merging, require review from Code Owners,
require status check **Agent config check**, block force pushes, restrict
deletions. As the sole owner you cannot approve your own PR; add a classmate
or TA as a second maintainer, or document this gap (DESIGN.md does).

## 7. Compile, check, push

```bash
gh aw compile issue-triage
python3 scripts/check_config.py
python3 evals/golden/tools/selftest_scripts.py
git add -A && git commit -m "Configure issue-triage agent" && git push
```

## 8. Smoke test

```bash
gh variable set TRIAGE_AGENT_ENABLED --body true
gh issue create --title "Smoke test: torch.ones(2).sum() returns 3 on CPU" \
  --body "### 🐛 Describe the bug
\`\`\`python
import torch; print(torch.ones(2).sum())  # tensor(3.)
\`\`\`
PyTorch version: 2.14.0"
gh run list --workflow issue-triage.lock.yml -L 3
gh run watch                       # pick the run
gh aw audit <run-id>               # model, tokens, AI credits, tool calls
gh run download <run-id> -D /tmp/smoke   # artifacts: skill_inventory.json, agent logs
```

Check that: the run is named `Triage #<n>`; `skill_inventory.json` lists
`pytorch-issue-triage`; the agent log shows it reading `SKILL.md` and running
`check_issue.py`; labels include `bot-triaged`; any comment ends with the
procedure footer. If the Copilot step fails with a model or entitlement
error, see "Fallback" in `evals/golden/README.md`.

Archive the smoke-test issue so it is not used as a duplicate candidate:

```bash
gh issue edit <n> --add-label eval-archive && gh issue close <n>
```
