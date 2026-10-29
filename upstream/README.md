# Upstream subset (read-only reference)

Files copied from [pytorch/pytorch](https://github.com/pytorch/pytorch) at commit
`b0a6c838fde64a95f680799bcdb142bd18498caa` (2026-10-27), under the BSD-3-Clause
licence in `LICENSE`. Hidden directories were renamed (`.github` -> `github`,
`.agents` -> `agents`) so GitHub does not treat them as live configuration in
this sandbox.

| Path | Why it is here |
|---|---|
| `CODEOWNERS`, `CONTRIBUTING.md`, `AI_POLICY.md`, `SECURITY.md` | Project conventions the agent and AGENTS.md refer to |
| `github/ISSUE_TEMPLATE/` | What upstream reporters fill in (bug, PT2 bug, feature, docs) |
| `agents/skills/triaging-issues/` | PyTorch's own Claude triage skill. Our label allowlist and routing rules are derived from it; DESIGN.md compares the two designs. |

Recreate with `scripts/import_upstream_subset.sh <commit>`.
