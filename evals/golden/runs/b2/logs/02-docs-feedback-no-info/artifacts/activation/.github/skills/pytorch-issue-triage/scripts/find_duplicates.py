#!/usr/bin/env python3
"""Rank existing issues by textual similarity to the issue being triaged.

Deterministic TF-IDF cosine similarity over word unigrams and bigrams from the
title (weighted x2) and the first 3000 characters of the body; identifiers are
split on dots/underscores and collect_env dumps are dropped. No network access and standard library only: the
pre-agent step (.github/scripts/build_triage_context.py) already wrote the
index of existing issues to the context directory.

The model still decides whether a candidate is a real duplicate; this script
only narrows the search and makes it reproducible.

Scores are only comparable within one repository snapshot. Thresholds were
set on the golden set (evals/golden): the true duplicate scored ~0.18 against
its original while unrelated MPS issues scored <=0.13, so the agent reads every
candidate >= 0.12 (at most 3) and decides itself.

Usage:
    python3 .claude/skills/pytorch-issue-triage/scripts/find_duplicates.py [--top 5]
"""
import argparse
import json
import math
import os
import re
import sys
from collections import Counter

STOP = set("""
a an and are as at be been but by can could do does for from has have how i if in into is it its
me my not of on or our so than that the their them then there these this to too was we were what when
where which while will with would you your issue bug error when using use used get got also just only
pytorch torch tensor tensors please thanks hi hello following code expected behavior behaviour describe
version versions output reproduce repro steps minimal example works work working does not doesn
""".split())

WORD_RE = re.compile(r"[a-z0-9]+")


def words(text):
    # split identifiers on dots and underscores so `storage_offset`,
    # "storage offset" and `x.storage_offset()` all produce the same words
    return [w for w in WORD_RE.findall(text.lower().replace("_", " "))
            if w not in STOP and len(w) >= 3 and not w.isdigit()]


def doc_tokens(issue):
    """Unigrams + bigrams; title counted twice; env dumps removed."""
    title = issue.get("title") or ""
    body = (issue.get("body") or "")[:3000]
    body = re.split(r"Collecting environment information", body)[0]
    toks = []
    for text, weight in ((title, 2), (body, 1)):
        w = words(text)
        toks += (w + [x + "_" + y for x, y in zip(w, w[1:])]) * weight
    return toks


def tfidf(docs):
    df = Counter()
    for d in docs:
        df.update(set(d))
    n = len(docs)
    vecs = []
    for d in docs:
        tf = Counter(d)
        vec = {t: (c / len(d)) * math.log((1 + n) / (1 + df[t]) + 1) for t, c in tf.items()} if d else {}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        vecs.append({t: v / norm for t, v in vec.items()})
    return vecs


def cosine(a, b):
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(t, 0.0) for t, v in a.items())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--context-dir", default=os.environ.get("TRIAGE_CONTEXT_DIR", ".triage-context"))
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--review-threshold", type=float, default=0.12,
                    help="candidates at or above this score must be read by the agent (max 3)")
    ap.add_argument("--threshold", type=float, default=0.35,
                    help="score at or above which a candidate is flagged likely_duplicate")
    args = ap.parse_args()

    try:
        with open(os.path.join(args.context_dir, "issue.json"), encoding="utf-8") as fh:
            issue = json.load(fh)
        with open(os.path.join(args.context_dir, "issues_index.json"), encoding="utf-8") as fh:
            index = json.load(fh)
    except FileNotFoundError as exc:
        print(json.dumps({"error": f"missing context file: {exc.filename}"}))
        sys.exit(2)

    index = [i for i in index if i.get("number") != issue.get("number")]
    if not index:
        print(json.dumps({"candidates": [], "likely_duplicate": None, "note": "no other issues in index"}))
        return

    vecs = tfidf([doc_tokens(issue)] + [doc_tokens(i) for i in index])
    q = vecs[0]
    scored = sorted(
        ({"number": i["number"], "title": i.get("title"), "state": i.get("state"),
          "score": round(cosine(q, v), 3)} for i, v in zip(index, vecs[1:])),
        key=lambda r: r["score"], reverse=True,
    )[: args.top]
    likely = scored[0] if scored and scored[0]["score"] >= args.threshold else None
    review = [c for c in scored if c["score"] >= args.review_threshold][:3]
    print(json.dumps({
        "review_threshold": args.review_threshold,
        "threshold": args.threshold,
        "review_candidates": review,
        "index_size": len(index),
        "candidates": scored,
        "likely_duplicate": likely,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
