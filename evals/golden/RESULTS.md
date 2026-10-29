# Evaluation results and failure analysis

Fill this in after each batch (`runs/<batch>/results.md` is generated; this
file is your analysis). Keep every batch; do not delete old ones.

## Batch `<bYYYYMMDD>` — <date>

- Configuration: commit `<sha>`, gh-aw `<version>`, model(s) seen in `gh aw audit`: `<...>`
- Expected outcomes committed in `<sha>` (before this batch).
- Summary: `<n>` cases, `<p>` PASS, `<f>` FAIL; precision `<x>`, recall `<y>`;
  bot events outside test issues: `<0?>`; close events: `<0?>`.
- Skill loaded: `<n>/<n>` runs have `pytorch-issue-triage` in `skill_inventory.json`
  and a `TRIAGE-SUMMARY procedure=pytorch-issue-triage/v1` line.
- AI credits / premium requests used: `<...>`

| Case | Verdict | What happened | Why | Action taken |
|---|---|---|---|---|
| 01 | | | | |

### Adversarial cases

- **A1** (claimed maintainer approval): what the agent attempted (see agent
  log and safe-output JSON), what was rejected and by which control, what
  was written.
- **A2** (hidden injection): same, plus whether threat detection flagged it.

### Governance tests

- Kill switch from phone: date, steps, screenshots in `docs/evidence/`,
  result (did a new issue get triaged? was a cancelled run's output written?).
- Burst test: `<k>` issues opened within `<m>` minutes; how many runs
  executed, queued, were rate-limited (pre-activation log), credits used.
