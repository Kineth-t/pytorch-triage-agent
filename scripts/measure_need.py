#!/usr/bin/env python3
"""Measure the issue-triage load on pytorch/pytorch for DESIGN.md.

For every issue opened in a window (bots and auto-generated DISABLED-test
issues excluded) it records, from the issue timeline:

  * hours until the first label was added, and who added it (human or bot);
  * hours until the first comment by someone other than the author;
  * whether a 'triaged' label was ever added, and when.

Run it for two windows to compare before/after PyTorch adopted its own
AI triage bot (introduction date: see --show-bot-history):

    gh auth login                                  # 5,000 API calls/hour
    python3 scripts/measure_need.py --since 2026-09-01 --until 2026-09-28 --out data/need-2026-09.json
    python3 scripts/measure_need.py --since 2025-09-01 --until 2025-09-28 --out data/need-2025-09.json
    python3 scripts/measure_need.py --show-bot-history

Limitations (copy into DESIGN.md): the search API returns at most 1,000
issues per query (use windows of <= 4 weeks); "first label" is not the same as
"correctly triaged"; issue-template labels and labels added by the reporter
count as labels; bots are recognised by login suffix [bot] and a short list
of known automation accounts; issues deleted or transferred away are missing.
"""
import argparse
import datetime as dt
import json
import statistics
import subprocess
import sys

REPO = "pytorch/pytorch"
KNOWN_BOTS = {"pytorch-bot", "pytorchmergebot", "facebook-github-bot", "github-actions", "pytorch-bot[bot]",
              "github-actions[bot]", "claude[bot]", "dependabot[bot]"}


def gh_json(*args):
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(out.stderr)
    return out.stdout


def is_bot(login):
    return not login or login.endswith("[bot]") or login in KNOWN_BOTS


def parse(ts):
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def search(since, until):
    q = f"repo:{REPO} is:issue created:{since}..{until}"
    out = gh_json("api", "-X", "GET", "search/issues", "-f", f"q={q}", "-f", "per_page=100",
                  "--paginate", "--jq", ".items[] | {number, title, user: .user.login, created_at}")
    return [json.loads(l) for l in out.splitlines() if l.strip()]


def timeline(n):
    out = gh_json("api", f"repos/{REPO}/issues/{n}/timeline", "--paginate", "--jq",
                  ".[] | {event, created_at: (.created_at // .submitted_at), "
                  "actor: (.actor.login // .user.login // null), label: (.label.name // null)}")
    return [json.loads(l) for l in out.splitlines() if l.strip()]


def summarise(rows):
    def med(xs):
        return round(statistics.median(xs), 2) if xs else None

    def share(pred):
        return round(sum(1 for r in rows if pred(r)) / len(rows), 3) if rows else None

    lab = [r["hours_to_first_label"] for r in rows if r["hours_to_first_label"] is not None]
    com = [r["hours_to_first_other_comment"] for r in rows if r["hours_to_first_other_comment"] is not None]
    tri = [r["hours_to_triaged"] for r in rows if r["hours_to_triaged"] is not None]
    return {
        "issues": len(rows),
        "median_hours_to_first_label": med(lab),
        "median_hours_to_first_comment_by_other": med(com),
        "median_hours_to_triaged": med(tri),
        "share_labelled_within_24h": share(lambda r: r["hours_to_first_label"] is not None and r["hours_to_first_label"] <= 24),
        "share_first_label_by_bot": share(lambda r: r["first_label_by_bot"] is True),
        "share_never_labelled": share(lambda r: r["hours_to_first_label"] is None),
        "share_never_triaged": share(lambda r: r["hours_to_triaged"] is None),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--sample", type=int, default=0, help="only fetch timelines for the first N issues")
    ap.add_argument("--out")
    ap.add_argument("--show-bot-history", action="store_true",
                    help="print the commits that added/changed PyTorch's own Claude triage workflow")
    a = ap.parse_args()

    if a.show_bot_history:
        out = gh_json("api", f"repos/{REPO}/commits?path=.github/workflows/claude-issue-triage.yml&per_page=100",
                      "--paginate", "--jq", '.[] | "\\(.commit.author.date) \\(.sha[0:10]) \\(.commit.message | split("\\n")[0])"')
        print(out)
        return
    if not (a.since and a.until):
        ap.error("--since and --until are required")

    issues = [i for i in search(a.since, a.until)
              if not is_bot(i["user"]) and not i["title"].startswith("DISABLED ")]
    if a.sample:
        issues = issues[: a.sample]
    rows = []
    for k, i in enumerate(issues, 1):
        t0 = parse(i["created_at"])
        first_label = first_comment = triaged = None
        first_label_by_bot = None
        for e in timeline(i["number"]):
            if not e.get("created_at"):
                continue
            h = (parse(e["created_at"]) - t0).total_seconds() / 3600
            if e["event"] == "labeled" and first_label is None:
                first_label, first_label_by_bot = h, is_bot(e["actor"])
            if e["event"] == "labeled" and e["label"] == "triaged" and triaged is None:
                triaged = h
            if e["event"] == "commented" and first_comment is None and e["actor"] != i["user"] and not is_bot(e["actor"]):
                first_comment = h
        rows.append({"number": i["number"], "hours_to_first_label": first_label, "first_label_by_bot": first_label_by_bot,
                     "hours_to_first_other_comment": first_comment, "hours_to_triaged": triaged})
        if k % 25 == 0:
            print(f"  {k}/{len(issues)}", file=sys.stderr)

    result = {"repo": REPO, "window": [a.since, a.until], "measured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
              "excluded": "bot authors and 'DISABLED ' auto-generated test issues",
              "summary": summarise(rows), "issues": rows}
    print(json.dumps(result["summary"], indent=2))
    if a.out:
        json.dump(result, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
