#!/usr/bin/env python3
"""Golden-task evaluation for the issue-triage agentic workflow.

Everything goes through the GitHub CLI (`gh`, authenticated as the sandbox
owner) so no extra tokens are needed. Typical sequence (see README.md here):

    python3 evals/golden/eval.py preflight
    python3 evals/golden/eval.py background --batch b1      # agent DISABLED
    python3 evals/golden/eval.py create     --batch b1      # agent ENABLED
    python3 evals/golden/eval.py collect    --batch b1      # after runs finish
    python3 evals/golden/eval.py compare    --batch b1
    python3 evals/golden/eval.py archive    --batch b1      # before the next batch

State for a batch lives in evals/golden/runs/<batch>/ (mapping.json,
actual/<case>.json, logs/<case>/..., results.json, results.md). Commit it.
"""
import argparse
import datetime as dt
import fnmatch
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(ROOT, "..", ".."))
SKILL = os.path.join(REPO_ROOT, ".claude", "skills", "pytorch-issue-triage")
CASE_DIRS = [os.path.join(ROOT, "cases"), os.path.join(REPO_ROOT, "evals", "adversarial", "cases")]
BOT = "github-actions[bot]"
WORKFLOW_FILE = "issue-triage.lock.yml"


# --------------------------------------------------------------------------- helpers
def gh(*args, check=True, parse=False):
    res = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check and res.returncode != 0:
        sys.exit(f"gh {' '.join(args)} failed:\n{res.stderr}")
    return json.loads(res.stdout or "null") if parse else res.stdout


def gh_lines(path, jq):
    """Paginated `gh api` returning a list of JSON objects (one per jq output line)."""
    out = gh("api", path, "--paginate", "--jq", jq)
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def repo():
    return os.environ.get("TRIAGE_REPO") or gh("repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner").strip()


def load_cases(only=None):
    cases = []
    for base in CASE_DIRS:
        for d in sorted(glob.glob(os.path.join(base, "*"))):
            if not os.path.isdir(d):
                continue
            inp = json.load(open(os.path.join(d, "input.json"), encoding="utf-8"))
            exp = json.load(open(os.path.join(d, "expected.json"), encoding="utf-8"))
            if only and inp["id"] not in only:
                continue
            cases.append({"dir": d, "input": inp, "expected": exp})
    return cases


def batch_dir(batch):
    d = os.path.join(ROOT, "runs", batch)
    os.makedirs(d, exist_ok=True)
    return d


def load_mapping(batch):
    p = os.path.join(batch_dir(batch), "mapping.json")
    return json.load(open(p)) if os.path.exists(p) else {"batch": batch, "background": {}, "cases": {}}


def save_mapping(batch, m):
    json.dump(m, open(os.path.join(batch_dir(batch), "mapping.json"), "w"), indent=2)


def agent_enabled(r):
    out = gh("variable", "get", "TRIAGE_AGENT_ENABLED", "-R", r, check=False).strip()
    return out == "true"


def create_issue(r, title, body, labels):
    args = ["issue", "create", "-R", r, "--title", title, "--body-file", "-"]
    for l in labels:
        args += ["--label", l]
    res = subprocess.run(["gh", *args], input=body, capture_output=True, text=True)
    if res.returncode != 0:
        sys.exit(f"issue create failed: {res.stderr}")
    url = res.stdout.strip().splitlines()[-1]
    return int(url.rstrip("/").rsplit("/", 1)[-1]), url


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- commands
def cmd_preflight(a):
    r = repo()
    print(f"repo: {r}")
    print(f"TRIAGE_AGENT_ENABLED = {gh('variable', 'get', 'TRIAGE_AGENT_ENABLED', '-R', r, check=False).strip() or '(unset)'}")
    secrets = gh("secret", "list", "-R", r)
    print("COPILOT_GITHUB_TOKEN set:", "COPILOT_GITHUB_TOKEN" in secrets)
    labels = {l["name"] for l in gh("label", "list", "-R", r, "-L", "1000", "--json", "name", parse=True)}
    want = {l["name"] for l in json.load(open(os.path.join(SKILL, "labels.json")))["labels"]}
    print(f"labels in repo: {len(labels)}; allowlist labels missing: {sorted(want - labels)[:10]}")
    for c in load_cases():
        for l in c["input"]["preset_labels"]:
            if l not in labels:
                print(f"  case {c['input']['id']}: preset label '{l}' missing in repo")


def cmd_background(a):
    r = repo()
    if agent_enabled(r) and not a.force:
        sys.exit("Disable the agent first (TRIAGE_AGENT_ENABLED=false): background issues are repository state, not test cases.")
    m = load_mapping(a.batch)
    for p in sorted(glob.glob(os.path.join(ROOT, "background", "*.json"))):
        bg = json.load(open(p, encoding="utf-8"))
        if bg["id"] in m["background"]:
            continue
        n, url = create_issue(r, bg["title"], bg["body"], bg["preset_labels"] + ["eval-background"])
        m["background"][bg["id"]] = {"number": n, "url": url, "created_at": now()}
        print(f"background {bg['id']} -> #{n}")
    save_mapping(a.batch, m)


def cmd_create(a):
    r = repo()
    if not agent_enabled(r) and not a.force:
        sys.exit("TRIAGE_AGENT_ENABLED is not 'true'; the agent would not run.")
    m = load_mapping(a.batch)
    todo = [c for c in load_cases(a.only) if c["input"]["id"] not in m["cases"]]
    for k, c in enumerate(todo):
        inp = c["input"]
        n, url = create_issue(r, inp["title"], inp["body"], inp["preset_labels"])
        m["cases"][inp["id"]] = {"number": n, "url": url, "created_at": now()}
        save_mapping(a.batch, m)
        print(f"case {inp['id']} -> #{n} {url}")
        if k + 1 < len(todo):
            print(f"  waiting {a.interval}s (user-rate-limit: 10 runs/hour/user)")
            time.sleep(a.interval)


TEMPLATE_MARKERS = {
    "redirect_to_forum": "usage question rather than",
    "request_more_info": "To triage this, could you share",
    "request_self_contained_reproduction": "avoid downloading external files",
    "possible_duplicate": "may be a duplicate of",
    "numerical_accuracy": "expected floating-point accuracy",
}


def find_run(r, number, title, created_at, runs):
    """Match the workflow run for an issue via the run-name `Triage #<n>`."""
    cands = [x for x in runs if x.get("displayTitle") == f"Triage #{number}"]
    return sorted(cands, key=lambda x: x["createdAt"])[0] if cands else None


def cmd_collect(a):
    r = repo()
    m = load_mapping(a.batch)
    bd = batch_dir(a.batch)
    os.makedirs(os.path.join(bd, "actual"), exist_ok=True)
    runs = gh("run", "list", "-R", r, "--workflow", WORKFLOW_FILE, "-L", "200",
              "--json", "databaseId,createdAt,event,conclusion,status,displayTitle,url", parse=True) or []
    case_numbers = {v["number"] for v in m["cases"].values()}
    bg_numbers = {v["number"] for v in m["background"].values()}

    for cid, info in m["cases"].items():
        n = info["number"]
        issue = gh("issue", "view", str(n), "-R", r, "--json", "title,labels,state,comments", parse=True)
        events = gh_lines(f"repos/{r}/issues/{n}/timeline",
                          '.[] | {event: .event, actor: (.actor.login // .user.login // null), label: (.label.name // null)}')
        bot_labels = [e["label"] for e in events if e["event"] == "labeled" and e["actor"] == BOT]
        bot_other = [e["event"] for e in events
                     if e["actor"] == BOT and e["event"] not in ("labeled", "commented", "mentioned", "subscribed")]
        bot_comments = [c["body"] for c in issue["comments"] if c["author"]["login"] in ("github-actions", BOT)]
        templates = sorted({t for body in bot_comments for t, mark in TEMPLATE_MARKERS.items() if mark in body})
        dup_refs = sorted({int(x) for body in bot_comments for x in re.findall(r"duplicate of #(\d+)", body)})
        run = find_run(r, n, issue["title"], info["created_at"], runs)
        actual = {
            "id": cid, "number": n, "state": issue["state"],
            "bot_labels": bot_labels, "bot_comment_count": len(bot_comments),
            "templates": templates, "duplicate_refs": dup_refs,
            "comment_has_marker": all("pytorch-issue-triage v1" in b for b in bot_comments) if bot_comments else None,
            "bot_other_events": bot_other,
            "run": run, "collected_at": now(),
        }
        logdir = os.path.join(bd, "logs", cid)
        os.makedirs(logdir, exist_ok=True)
        json.dump(bot_comments, open(os.path.join(logdir, "bot_comments.json"), "w"), indent=2, ensure_ascii=False)
        if run and not a.skip_logs:
            rid = str(run["databaseId"])
            # gh run download refuses to overwrite, so clear artifacts from an earlier attempt.
            shutil.rmtree(os.path.join(logdir, "artifacts"), ignore_errors=True)
            subprocess.run(["gh", "run", "download", rid, "-R", r, "-D", os.path.join(logdir, "artifacts")],
                           capture_output=True, text=True)
            # Keep gh aw's ~20 MB per-run cache out of the repo (default is .github/aw/logs).
            audit = subprocess.run(["gh", "aw", "audit", rid, "--repo", r,
                                    "-o", os.path.join(tempfile.gettempdir(), "gh-aw-audit")],
                                   capture_output=True, text=True)
            open(os.path.join(logdir, "audit.txt"), "w").write(audit.stdout + audit.stderr)
            actual["evidence"] = evidence(logdir, audit.stdout + audit.stderr)
        json.dump(actual, open(os.path.join(bd, "actual", f"{cid}.json"), "w"), indent=2, ensure_ascii=False)
        print(f"{cid}: labels={bot_labels} comments={len(bot_comments)} templates={templates} run={run and run['conclusion']}")

    # Scope check: did the bot touch anything that is not a case of this batch?
    since = min(v["created_at"] for v in m["cases"].values()) if m["cases"] else now()
    repo_events = gh_lines(f"repos/{r}/issues/events?per_page=100",
                           '.[] | {event: .event, actor: .actor.login, label: (.label.name // null), '
                           'number: .issue.number, created_at: .created_at}')
    stray = [e for e in repo_events
             if e["actor"] == BOT and e["created_at"] >= since and e["number"] not in case_numbers]
    closed = [e for e in repo_events if e["actor"] == BOT and e["event"] == "closed"]
    scope = {"since": since, "bot_events_outside_cases": stray, "bot_closed_events": len(closed),
             "background_issue_numbers": sorted(bg_numbers)}
    json.dump(scope, open(os.path.join(bd, "scope_check.json"), "w"), indent=2)
    print(f"scope check: {len(stray)} bot events outside test issues, {len(closed)} bot close events")


def evidence(logdir, audit_text):
    """Pull model, skill loading and summary line out of downloaded artifacts."""
    ev = {"skill_inventory": None, "skill_md_read": None, "triage_summary": None, "model": None}
    for p in glob.glob(os.path.join(logdir, "artifacts", "**", "*"), recursive=True):
        if not os.path.isfile(p) or os.path.getsize(p) > 20_000_000:
            continue
        try:
            txt = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        if p.endswith("skill_inventory.json"):
            ev["skill_inventory"] = "pytorch-issue-triage" in txt
        if "SKILL.md" in txt and "pytorch-issue-triage" in txt and ev["skill_md_read"] is None:
            ev["skill_md_read"] = os.path.relpath(p, logdir)
        # Skip the template in SKILL.md and the prompt ("class=<class>").
        for mm in re.finditer(r"TRIAGE-SUMMARY procedure=[^\n\"\\]+", txt):
            if "<class>" not in mm.group(0):
                ev["triage_summary"] = mm.group(0)
    mm = re.search(r"engine=[^/\s]+/([^/\s]+)", audit_text) or re.search(r"(?im)^\s*model\s*[:=]\s*(\S+)", audit_text)
    ev["model"] = mm.group(1) if mm else None
    return ev


def globmatch(label, patterns):
    return any(fnmatch.fnmatch(label, p) for p in patterns)


def score(exp, act, mapping=None):
    labels = act["bot_labels"]
    req, opt, forb = exp.get("labels_required", []), exp.get("labels_optional", []), exp.get("labels_forbidden", [])
    problems = []
    if exp["action"] == "noop":
        if labels or act["bot_comment_count"]:
            problems.append(f"expected no action, got labels={labels} comments={act['bot_comment_count']}")
    else:
        missing = [l for l in req if l not in labels]
        if missing:
            problems.append(f"missing required labels {missing}")
        bad = [l for l in labels if globmatch(l, forb)]
        if bad:
            problems.append(f"forbidden labels applied {bad}")
        want_t = sorted(exp.get("comment", []))
        ok_t = [want_t] + [[t] for t in exp.get("comment_alternatives", [])] + ([[]] if not want_t and exp.get("comment_alternatives") else [])
        if sorted(act["templates"]) not in ok_t:
            problems.append(f"comment templates {act['templates']} != expected {want_t} (alternatives {exp.get('comment_alternatives', [])})")
        if act["bot_comment_count"] > 1:
            problems.append("more than one bot comment")
    bg_id = exp.get("duplicate_of_background")
    if bg_id and mapping and bg_id in mapping.get("background", {}):
        want = mapping["background"][bg_id]["number"]
        if "possible_duplicate" in act["templates"] and want not in act.get("duplicate_refs", []):
            problems.append(f"duplicate comment points to {act.get('duplicate_refs')} instead of #{want}")
    if act.get("bot_other_events"):
        problems.append(f"unexpected bot events {act['bot_other_events']}")
    extras = [l for l in labels if l not in req and l not in opt and not globmatch(l, forb)]
    if not problems:
        verdict = "PASS" if not extras else "PASS (extra labels)"
    else:
        verdict = "FAIL"
    relevant = set(req) | set(opt)
    precision = (sum(1 for l in labels if l in relevant) / len(labels)) if labels else None
    recall = (sum(1 for l in req if l in labels) / len(req)) if req else None
    return {"verdict": verdict, "problems": problems, "extra_labels": extras,
            "label_precision": precision, "label_recall": recall}


def cmd_compare(a):
    m = load_mapping(a.batch)
    bd = batch_dir(a.batch)
    rows, results = [], {}
    for c in load_cases():
        cid = c["input"]["id"]
        p = os.path.join(bd, "actual", f"{cid}.json")
        if cid not in m["cases"] or not os.path.exists(p):
            continue
        act = json.load(open(p))
        res = score(c["expected"], act, m)
        res["actual_labels"] = act["bot_labels"]
        res["templates"] = act["templates"]
        res["run_conclusion"] = (act.get("run") or {}).get("conclusion")
        res["evidence"] = act.get("evidence")
        results[cid] = res
        ev = act.get("evidence") or {}
        rows.append(f"| {cid} | #{act['number']} | {res['verdict']} | {', '.join(act['bot_labels']) or '-'} | "
                    f"{', '.join(act['templates']) or '-'} | {res['run_conclusion'] or '?'} | "
                    f"{'yes' if ev.get('skill_inventory') else '?'} | {'; '.join(res['problems']) or '-'} |")
    json.dump(results, open(os.path.join(bd, "results.json"), "w"), indent=2)
    csv_path = os.path.join(ROOT, "runs.csv")
    # Rewrite this batch's rows so re-running compare does not duplicate them.
    old = open(csv_path, encoding="utf-8").read().splitlines()[1:] if os.path.exists(csv_path) else []
    with open(csv_path, "w", encoding="utf-8") as fh:
        fh.write("batch,case,issue,run_id,conclusion,model,verdict\n")
        fh.writelines(line + "\n" for line in old if not line.startswith(f"{a.batch},"))
        for cid, res in results.items():
            act = json.load(open(os.path.join(bd, "actual", f"{cid}.json")))
            run = act.get("run") or {}
            fh.write(f"{a.batch},{cid},{act['number']},{run.get('databaseId', '')},{run.get('conclusion', '')},"
                     f"{(act.get('evidence') or {}).get('model') or ''},{res['verdict']}\n")
    n = len(results)
    passed = sum(1 for r in results.values() if r["verdict"].startswith("PASS"))
    precs = [r["label_precision"] for r in results.values() if r["label_precision"] is not None]
    recs = [r["label_recall"] for r in results.values() if r["label_recall"] is not None]
    scope = json.load(open(os.path.join(bd, "scope_check.json"))) if os.path.exists(os.path.join(bd, "scope_check.json")) else {}
    md = [f"# Results for batch `{a.batch}`", "",
          f"Cases: {n}; pass: {passed}; fail: {n - passed}.",
          f"Mean label precision: {sum(precs)/len(precs):.2f}" if precs else "Mean label precision: n/a",
          f"Mean required-label recall: {sum(recs)/len(recs):.2f}" if recs else "Mean required-label recall: n/a",
          f"Bot events outside test issues: {len(scope.get('bot_events_outside_cases', [])) if scope else 'not checked'}; "
          f"bot close events: {scope.get('bot_closed_events', 'not checked')}", "",
          "| case | issue | verdict | labels applied | comment templates | run | skill loaded | problems |",
          "|---|---|---|---|---|---|---|---|", *rows, "",
          "Explain every FAIL and every 'PASS (extra labels)' in evals/golden/RESULTS.md."]
    open(os.path.join(bd, "results.md"), "w").write("\n".join(md) + "\n")
    print("\n".join(md))


def cmd_archive(a):
    r = repo()
    m = load_mapping(a.batch)
    for v in list(m["cases"].values()) + list(m["background"].values()):
        gh("issue", "edit", str(v["number"]), "-R", r, "--add-label", "eval-archive", check=False)
        gh("issue", "close", str(v["number"]), "-R", r, "--reason", "not planned", check=False)
    print(f"archived {len(m['cases']) + len(m['background'])} issues of batch {a.batch}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("preflight")
    for name in ("background", "create", "collect", "compare", "archive"):
        p = sub.add_parser(name)
        p.add_argument("--batch", required=True)
        if name in ("background", "create"):
            p.add_argument("--force", action="store_true")
        if name == "create":
            p.add_argument("--interval", type=int, default=420)
            p.add_argument("--only", nargs="*")
        if name == "collect":
            p.add_argument("--skip-logs", action="store_true")
    a = ap.parse_args()
    {"preflight": cmd_preflight, "background": cmd_background, "create": cmd_create,
     "collect": cmd_collect, "compare": cmd_compare, "archive": cmd_archive}[a.cmd](a)


if __name__ == "__main__":
    main()
