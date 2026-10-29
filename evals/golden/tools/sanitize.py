"""Make an upstream issue body safe to re-post in the sandbox.

Re-posting raw upstream text would (a) @-mention real PyTorch maintainers and
(b) create "mentioned this issue" backlinks on real pytorch/pytorch issues.
Both would be spam on a project we have no permission to touch. So:

* `cc @a @b` lines are removed (they are the upstream bot's auto-cc, added
  after triage, and are not information the original reporter wrote);
* remaining @handles lose the @;
* #123, owner/repo#123 and github.com/.../issues/123 links become plain text
  "upstream issue 123", which GitHub does not link.
"""
import re


def sanitize(body: str) -> str:
    body = body or ""
    body = re.sub(r"(?m)^\s*cc(\s+@[\w-]+)+\s*$", "", body)
    body = re.sub(r"https?://github\.com/pytorch/pytorch/(issues|pull)/(\d+)\S*",
                  r"upstream issue \2", body)
    body = re.sub(r"\b[\w.-]+/[\w.-]+#(\d+)", r"upstream issue \1", body)
    body = re.sub(r"(?<![\w&/])#(\d{3,})\b", r"upstream issue \1", body)
    body = re.sub(r"(?<![\w`])@([A-Za-z0-9][\w-]*)", r"\1", body)
    return body.rstrip() + "\n"
