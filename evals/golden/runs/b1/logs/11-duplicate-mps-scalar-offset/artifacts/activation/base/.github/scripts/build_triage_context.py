#!/usr/bin/env python3
"""Pre-agent step: write the issue and an index of existing issues to disk.

Runs as a custom `steps:` entry in .github/workflows/issue-triage.md, i.e.
OUTSIDE the agent sandbox, with the workflow's read-only GITHUB_TOKEN. It does
the network work so the skill scripts (check_issue.py, find_duplicates.py) can
run inside the firewalled agent container with no network and no token.

Output (in $TRIAGE_CONTEXT_DIR, default .triage-context/):
  issue.json         the issue being triaged (title, body, labels, author association)
  issues_index.json  up to MAX_INDEX other issues (open and closed; PRs and
                     issues labelled eval-archive excluded)

Usage: python3 .github/scripts/build_triage_context.py <issue-number>
"""
import json
import os
import sys
import urllib.request

API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
REPO = os.environ["GITHUB_REPOSITORY"]
TOKEN = os.environ["GH_TOKEN"]
OUT = os.environ.get("TRIAGE_CONTEXT_DIR", ".triage-context")
MAX_INDEX = int(os.environ.get("TRIAGE_MAX_INDEX", "500"))


def get(path):
    req = urllib.request.Request(
        f"{API}{path}",
        headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def slim(i):
    return {
        "number": i["number"],
        "title": i.get("title"),
        "body": (i.get("body") or "")[:6000],
        "state": i.get("state"),
        "labels": [l["name"] for l in i.get("labels", [])],
        "author_association": i.get("author_association"),
        "created_at": i.get("created_at"),
    }


def main():
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        sys.exit("usage: build_triage_context.py <issue-number>")
    number = int(sys.argv[1])
    os.makedirs(OUT, exist_ok=True)

    issue = slim(get(f"/repos/{REPO}/issues/{number}"))
    with open(os.path.join(OUT, "issue.json"), "w", encoding="utf-8") as fh:
        json.dump(issue, fh, indent=1, ensure_ascii=False)

    index, page = [], 1
    while len(index) < MAX_INDEX and page <= 10:
        batch = get(f"/repos/{REPO}/issues?state=all&per_page=100&page={page}&sort=created&direction=desc")
        if not batch:
            break
        index += [
            slim(i) for i in batch
            if "pull_request" not in i
            and i["number"] != number
            # Copies from earlier golden-task runs are archived with this label
            # so they are not reported as duplicates of the rerun.
            and not any(l["name"] == "eval-archive" for l in i.get("labels", []))
        ]
        page += 1
    with open(os.path.join(OUT, "issues_index.json"), "w", encoding="utf-8") as fh:
        json.dump(index[:MAX_INDEX], fh, indent=1, ensure_ascii=False)

    print(f"wrote issue #{number} and an index of {len(index[:MAX_INDEX])} issues to {OUT}/")


if __name__ == "__main__":
    main()
