#!/usr/bin/env python3
"""Validate a proposed label set before the agent emits add_labels.

This is an early, explanatory check. The HARD enforcement is the
`safe-outputs.add-labels.allowed` list in .github/workflows/issue-triage.md,
which rejects any label outside the allowlist even if the model skips this
script. This script additionally checks routing rules that a flat allowlist
cannot express.

Usage:
    python3 .claude/skills/pytorch-issue-triage/scripts/validate_labels.py "module: mps" "module: crash" "bot-triaged"

Prints JSON {"ok": bool, "errors": [...], "warnings": [...], "labels": [...]}
and exits 1 when there are errors.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LABELS_FILE = os.path.join(HERE, "..", "labels.json")


def validate(proposed, existing=()):
    with open(LABELS_FILE, encoding="utf-8") as fh:
        cfg = json.load(fh)
    allowed = {l["name"] for l in cfg["labels"]}
    reserved = {r["name"]: r["reason"] for r in cfg["reserved_for_humans"]}
    marker = cfg["required_marker"]
    max_labels = cfg["max_labels_per_issue"]

    errors, warnings = [], []
    labels = []
    for l in proposed:
        l = l.strip()
        if not l:
            continue
        if l in labels:
            warnings.append(f"duplicate label '{l}' removed")
            continue
        labels.append(l)

    for l in labels:
        if l in reserved:
            errors.append(f"'{l}' is reserved for humans: {reserved[l]}")
        elif l not in allowed:
            close = sorted(a for a in allowed if l.lower() in a.lower() or a.lower() in l.lower())[:3]
            hint = f" (did you mean: {', '.join(close)})" if close else ""
            errors.append(f"'{l}' is not in labels.json{hint}")
        if l in existing:
            warnings.append(f"'{l}' is already on the issue; omit it")

    if marker not in labels:
        errors.append(f"the marker label '{marker}' must be included")
    if len(labels) > max_labels:
        errors.append(f"{len(labels)} labels proposed; maximum is {max_labels}")

    oncall = [l for l in labels if l.startswith("oncall:")]
    modules = [l for l in labels if l.startswith("module:")]
    non_pt2_oncall = [l for l in oncall if l not in ("oncall: pt2", "oncall: cpu inductor")]
    if len(oncall) > 2:
        errors.append("more than two oncall: labels; route to one queue (two only for pt2 + distributed)")
    if non_pt2_oncall and modules and "oncall: pt2" not in oncall:
        errors.append(f"redirect to {non_pt2_oncall[0]} must not carry module: labels; that team labels its own queue")
    if "oncall: pt2" in oncall and not modules:
        errors.append("'oncall: pt2' requires at least one module: label (fallback: 'module: compile ux')")
    types = [l for l in labels if l in ("feature", "enhancement", "function request")]
    if len(types) > 1:
        errors.append(f"pick one type label, not {types}")
    if "module: correctness (silent)" in labels and "triage review" not in labels:
        errors.append("silent wrong results must be escalated: add 'triage review' (Step 6)")
    if "triage review" in labels and not (modules or oncall):
        warnings.append("'triage review' goes on top of routing labels; add module:/oncall: unless off-topic")

    if "better-on-discuss-forum" in labels and (modules or oncall):
        warnings.append("question redirected to the forum normally needs no routing labels")

    return {"ok": not errors, "errors": errors, "warnings": warnings, "labels": labels}


def main():
    args = sys.argv[1:]
    existing = []
    if "--existing" in args:
        i = args.index("--existing")
        existing = [x for x in args[i + 1:]]
        args = args[:i]
    result = validate(args, existing)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
