#!/usr/bin/env python3
"""Make the sandbox's label set equal to the skill's allowlist (plus human-only labels).

This is what turns labels.json into a HARD control: the add-labels safe output
cannot create labels (create-if-missing is false), so the agent can only apply
labels that exist here - and the human-only ones are additionally `blocked:`
in the workflow.

    python3 scripts/setup_sandbox_labels.py            # dry run
    python3 scripts/setup_sandbox_labels.py --apply    # create/update labels
    python3 scripts/setup_sandbox_labels.py --apply --prune   # also delete other labels
                                                       # (e.g. GitHub defaults 'bug', 'question')
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LABELS = os.path.join(HERE, "..", ".claude", "skills", "pytorch-issue-triage", "labels.json")
EXTRA = {  # bookkeeping labels used by the evaluation, blocked for the agent via "eval-*"
    "eval-archive": ("cfd3d7", "Golden-task copy from an earlier evaluation batch (excluded from duplicate search)"),
    "eval-background": ("cfd3d7", "Pre-existing issue recreated as repository state for the evaluation"),
}


def color(name):
    if name.startswith("module:"):
        return "c5def5"
    if name.startswith("oncall:"):
        return "fbca04"
    if name in ("triage review", "bot-triaged"):
        return "d93f0b"
    return "ededed"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--prune", action="store_true")
    ap.add_argument("-R", "--repo", default=None)
    a = ap.parse_args()
    cfg = json.load(open(LABELS, encoding="utf-8"))
    want = {l["name"]: (color(l["name"]), (l.get("description") or "")[:100]) for l in cfg["labels"]}
    for r in cfg["reserved_for_humans"]:
        want[r["name"]] = ("0e8a16", ("Human-only: " + r["reason"])[:100])
    want.update(EXTRA)
    rflag = ["-R", a.repo] if a.repo else []
    have = {l["name"] for l in json.loads(subprocess.check_output(
        ["gh", "label", "list", *rflag, "-L", "2000", "--json", "name"], text=True))}
    create = sorted(set(want) - have)
    prune = sorted(have - set(want))
    print(f"{len(want)} wanted, {len(have)} present, {len(create)} to create, {len(prune)} not in allowlist")
    if prune:
        print("  not in allowlist:", ", ".join(prune[:20]), "..." if len(prune) > 20 else "")
    if not a.apply:
        print("dry run; pass --apply")
        return
    for name, (col, desc) in sorted(want.items()):
        subprocess.run(["gh", "label", "create", name, *rflag, "--color", col, "--description", desc, "--force"],
                       check=True, capture_output=True)
    if a.prune:
        for name in prune:
            subprocess.run(["gh", "label", "delete", name, *rflag, "--yes"], check=True, capture_output=True)
    print("done")


if __name__ == "__main__":
    sys.exit(main())
