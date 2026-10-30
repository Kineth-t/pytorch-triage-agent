#!/usr/bin/env python3
"""Deterministic facts about the issue being triaged (no model judgement).

Reads the context file written by .github/scripts/build_triage_context.py and
prints a JSON object. The SKILL.md procedure uses these facts to decide whether
to stop early (already routed / already triaged) and which templates apply.

Usage:
    python3 .claude/skills/pytorch-issue-triage/scripts/check_issue.py [--context-dir DIR]

Exit code is always 0 unless the context file is missing (exit 2).
Standard library only, so it runs inside the agent sandbox without network.
"""
import argparse
import json
import os
import re
import sys

EXTERNAL_FILE_PATTERNS = [
    r"drive\.google\.com",
    r"docs\.google\.com/uc",
    r"dropbox\.com",
    r"onedrive\.live\.com|1drv\.ms",
    r"mega\.nz",
    r"wetransfer\.com|we\.tl/",
    r"huggingface\.co/[^\s)]+/(resolve|blob)/[^\s)]+",
    r"https?://\S+\.(zip|tar\.gz|tgz|pt|pth|pkl|pickle|safetensors|onnx|bin|ckpt)\b",
]

SECURITY_PATTERNS = [
    r"\bCVE-\d{4}-\d+",
    r"\bremote code execution\b|\bRCE\b",
    r"\barbitrary (code|command) execution\b",
    r"\bvulnerabilit(y|ies)\b",
    r"\bexploit(able|s|ed)?\b",
    r"weights_only\s*=\s*True.{0,80}(bypass|unrestricted|arbitrary)",
    r"\bdeserializ\w+ (attack|gadget)\b",
]

# Phrases that try to steer an automated agent. Their presence never changes
# what the agent is ALLOWED to do (that is fixed by safe-outputs); it only
# makes the procedure escalate to a human with 'triage review'.
INJECTION_PATTERNS = [
    r"ignore (all |any |your |the )?(previous|prior|above|earlier) (instructions|rules|prompt)",
    r"ignore (the|your) (skill|procedure|rules)",
    r"(maintainer|admin|owner|core team)s?\W{0,3}(has |have )?(approv|authoriz|sign(ed)? off)",
    r"\bapproved by (the )?(pytorch )?(maintainers|admins|core team)",
    r"\b(close|delete|lock) (all|every|the other|these) (stale |open |other )?(issues|prs|pull requests)\b",
    r"\byou are (now )?(the|a|operating in) (triage |maintainer |admin |developer )?(bot|agent|assistant|mode)\b",
    r"\b(maintainer|admin|developer|god) mode\b",
    r"\b(system|developer) prompt\b",
    r"\b(note|instructions?|message) to (the )?(ai|llm|triage|copilot|claude)\b",
    r"<!--(?:(?!-->).){0,3000}?\b(agent|assistant|bot|copilot|claude|llm|ai)\b",
    r"\b(GITHUB_TOKEN|COPILOT_GITHUB_TOKEN|environment variables?|secrets?)\b.{0,60}\b(print|post|reveal|comment|send|leak|containing)\b",
    r"\b(print|post|reveal|comment|send|leak)\b.{0,60}\b(GITHUB_TOKEN|COPILOT_GITHUB_TOKEN|environment variables?)\b",
    r"\b(add|apply) (the )?(labels? )?['\"`]?(high priority|triaged|security)['\"`]?",
    r"\b(to|on) every (other )?(open )?issue\b",
]

PT2_PATTERNS = [
    r"torch\.compile", r"\binductor\b", r"\bdynamo\b", r"\baot(inductor|autograd|dispatch)\b",
    r"\btorch\.export\b", r"\bfullgraph\b", r"\bgraph break", r"\bfake ?tensor\b",
]

VERSION_PATTERNS = [
    r"PyTorch version\s*:\s*\S+",
    r"torch(==|\s+)\d+\.\d+",
    r"torch\.__version__",
    r"\b2\.\d{1,2}(\.\d+)?(\+cu\d+|\.dev\d+)?\b",
]


def load_issue(context_dir):
    path = os.path.join(context_dir, "issue.json")
    if not os.path.exists(path):
        print(json.dumps({"error": f"missing {path}; the pre-agent step did not run"}))
        sys.exit(2)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def find_all(patterns, text, flags=re.IGNORECASE | re.DOTALL):
    hits = []
    for pat in patterns:
        for m in re.finditer(pat, text, flags):
            snippet = m.group(0)
            if len(snippet) > 120:
                snippet = snippet[:117] + "..."
            hits.append(snippet)
    # de-duplicate, keep order
    seen = set()
    return [h for h in hits if not (h in seen or seen.add(h))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--context-dir", default=os.environ.get("TRIAGE_CONTEXT_DIR", ".triage-context"))
    args = ap.parse_args()

    issue = load_issue(args.context_dir)
    title = issue.get("title") or ""
    body = issue.get("body") or ""
    text = f"{title}\n{body}"
    labels = [l if isinstance(l, str) else l.get("name", "") for l in issue.get("labels", [])]

    oncall = [l for l in labels if l.startswith("oncall:")]
    already_triaged = "triaged" in labels
    already_routed = bool(oncall)
    bot_already_ran = "bot-triaged" in labels

    skip_reason = None
    if already_triaged:
        skip_reason = "issue already carries 'triaged' (a human finished triage)"
    elif already_routed:
        skip_reason = f"issue already routed to {', '.join(oncall)}; that queue owns it"
    elif bot_already_ran:
        skip_reason = "issue already carries 'bot-triaged'; do not triage twice"

    code_blocks = len(re.findall(r"```", body)) // 2
    has_traceback = bool(re.search(r"Traceback \(most recent call last\)|RuntimeError:|Error:|Segmentation fault|SIGSEGV", body))
    has_collect_env = bool(re.search(r"Collecting environment information|PyTorch version\s*:", body))

    facts = {
        "number": issue.get("number"),
        "title": title,
        "author_association": issue.get("author_association"),
        "existing_labels": labels,
        "skip": skip_reason is not None,
        "skip_reason": skip_reason,
        "body_chars": len(body),
        "code_blocks": code_blocks,
        "has_traceback": has_traceback,
        "has_collect_env": has_collect_env,
        "versions_mentioned": find_all(VERSION_PATTERNS, body)[:5],
        "low_information": len(body.strip()) < 200 and code_blocks == 0 and not has_traceback,
        "external_file_links": find_all(EXTERNAL_FILE_PATTERNS, body),
        "security_signals": find_all(SECURITY_PATTERNS, text),
        "injection_signals": find_all(INJECTION_PATTERNS, text),
        "pt2_signals": find_all(PT2_PATTERNS, text)[:5],
    }
    print(json.dumps(facts, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
