#!/usr/bin/env python3
"""Run the deterministic skill scripts on every golden/adversarial input.

No model involved. Builds a fake .triage-context per case (the case as the
issue, all earlier inputs as the index), then checks the facts that do not
need judgement:

  * cases expected to be no-ops are flagged skip=true by check_issue.py;
  * adversarial cases raise injection_signals, golden cases do not;
  * every expected required-label set passes validate_labels.py;
  * the known duplicate's original is among find_duplicates.py review candidates.

Exit 1 on any failure. Used by .github/workflows/config-check.yml.
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
S = os.path.join(ROOT, ".claude", "skills", "pytorch-issue-triage", "scripts")


def load(pattern):
    out = []
    for p in sorted(glob.glob(os.path.join(ROOT, pattern))):
        d = os.path.dirname(p)
        out.append((json.load(open(p, encoding="utf-8")), json.load(open(os.path.join(d, "expected.json"), encoding="utf-8"))))
    return out


def run(script, *args):
    r = subprocess.run([sys.executable, os.path.join(S, script), *args], capture_output=True, text=True)
    return r.returncode, json.loads(r.stdout)


def main():
    bgs = [json.load(open(p, encoding="utf-8")) for p in sorted(glob.glob(os.path.join(ROOT, "evals/golden/background/*.json")))]
    golden = load("evals/golden/cases/*/input.json")
    adv = load("evals/adversarial/cases/*/input.json")
    numbered = [(1000 + k, b, None) for k, b in enumerate(bgs)]
    numbered += [(2000 + k, i, e) for k, (i, e) in enumerate(golden + adv)]
    bg_num = {b["id"]: n for n, b, _ in numbered if _ is None}

    def as_issue(n, it):
        return {"number": n, "title": it["title"], "body": it["body"], "state": "open",
                "labels": it["preset_labels"], "author_association": "NONE"}

    failures = []
    tmp = tempfile.mkdtemp()
    try:
        for n, it, exp in numbered:
            if exp is None:
                continue
            ctx = os.path.join(tmp, it["id"])
            os.makedirs(ctx)
            json.dump(as_issue(n, it), open(os.path.join(ctx, "issue.json"), "w"))
            json.dump([as_issue(m, o) for m, o, _ in numbered if m < n], open(os.path.join(ctx, "issues_index.json"), "w"))
            _, facts = run("check_issue.py", "--context-dir", ctx)
            if (exp["action"] == "noop") != facts["skip"]:
                failures.append(f"{it['id']}: skip={facts['skip']} but expected action={exp['action']}")
            is_adv = it["id"].startswith("A")
            if is_adv and not facts["injection_signals"]:
                failures.append(f"{it['id']}: adversarial input raised no injection_signals")
            if not is_adv and facts["injection_signals"]:
                failures.append(f"{it['id']}: false-positive injection_signals {facts['injection_signals']}")
            if exp["action"] == "act":
                code, v = run("validate_labels.py", *exp["labels_required"])
                if code != 0:
                    failures.append(f"{it['id']}: expected labels fail validation: {v['errors']}")
            if exp.get("duplicate_of_background"):
                _, dup = run("find_duplicates.py", "--context-dir", ctx)
                want = bg_num[exp["duplicate_of_background"]]
                if want not in [c["number"] for c in dup["review_candidates"]]:
                    failures.append(f"{it['id']}: original not among review candidates {dup['candidates'][:3]}")
            print(f"ok  {it['id']}" if not any(f.startswith(it['id']) for f in failures) else f"FAIL {it['id']}")
    finally:
        shutil.rmtree(tmp)
    if failures:
        print("\n".join(failures))
        sys.exit(1)
    print(f"all {len(golden) + len(adv)} cases passed the deterministic self-test")


if __name__ == "__main__":
    main()
