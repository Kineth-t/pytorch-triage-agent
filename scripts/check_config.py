#!/usr/bin/env python3
"""Consistency checks between the files that together define the agent.

Run locally or in CI (.github/workflows/config-check.yml). Fails if:
  * a label reserved for humans in labels.json is not blocked by the workflow;
  * an allowlisted label would be blocked (so the agent could never apply it);
  * the compiled .lock.yml is older than its .md source (forgot `gh aw compile`);
  * the lock file grants write permissions to the agent job or enables
    safe outputs other than add_labels / add_comment / noop / framework reports;
  * SKILL.md refers to a script that does not exist.
"""
import fnmatch
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SKILL = os.path.join(ROOT, ".claude", "skills", "pytorch-issue-triage")
WF = os.path.join(ROOT, ".github", "workflows", "issue-triage.md")
LOCK = os.path.join(ROOT, ".github", "workflows", "issue-triage.lock.yml")
ALLOWED_TOOLS = {"add_comment", "add_labels", "noop", "report_incomplete", "report_missing_data", "report_missing_tool"}

errors = []
cfg = json.load(open(os.path.join(SKILL, "labels.json"), encoding="utf-8"))
wf = open(WF, encoding="utf-8").read()
blocked = re.findall(r'^\s+- "([^"]+)"', wf.split("blocked:", 1)[1].split("max:", 1)[0], flags=re.M)

for r in cfg["reserved_for_humans"]:
    if not any(fnmatch.fnmatch(r["name"], p) for p in blocked):
        errors.append(f"reserved label '{r['name']}' is not blocked in issue-triage.md")
for l in cfg["labels"]:
    if any(fnmatch.fnmatch(l["name"], p) for p in blocked):
        errors.append(f"allowlisted label '{l['name']}' is blocked by a pattern; the agent could never apply it")

lock = open(LOCK, encoding="utf-8").read()
m = re.search(r'"body_hash":"([0-9a-f]+)"', lock)
if not m:
    errors.append("lock file has no gh-aw metadata; recompile with `gh aw compile`")
manifest = json.loads(re.search(r"^# gh-aw-manifest: (\{.*\})$", lock, flags=re.M).group(1))
for server in manifest.get("mcp_servers", []):
    if server["name"] == "safeoutputs":
        extra = set(server["tools"]) - ALLOWED_TOOLS
        if extra:
            errors.append(f"unexpected safe-output tools enabled: {sorted(extra)}")
agent_job = lock.split("\n  agent:\n", 1)[1].split("\n  conclusion:\n", 1)[0] if "\n  agent:\n" in lock else ""
perm = re.search(r"\n    permissions:\n((?:      .+\n)+)", agent_job)
if perm and "write" in perm.group(1):
    errors.append(f"agent job has write permissions:\n{perm.group(1)}")
if os.path.getmtime(LOCK) + 1 < os.path.getmtime(WF) and os.environ.get("CI") is None:
    errors.append("issue-triage.md is newer than its .lock.yml; run `gh aw compile`")

skill_md = open(os.path.join(SKILL, "SKILL.md"), encoding="utf-8").read()
for script in set(re.findall(r"scripts/([\w_]+\.py)", skill_md)):
    if not os.path.exists(os.path.join(SKILL, "scripts", script)):
        errors.append(f"SKILL.md references missing script {script}")

if errors:
    print("config check FAILED:")
    for e in errors:
        print("  -", e)
    sys.exit(1)
print(f"config check OK ({len(cfg['labels'])} allowlisted labels, {len(blocked)} blocked patterns)")
