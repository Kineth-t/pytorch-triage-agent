#!/usr/bin/env bash
# Re-import the read-only upstream subset at a given pytorch/pytorch commit.
set -euo pipefail
COMMIT="${1:-main}"
TMP="$(mktemp -d)"
git clone -q --filter=blob:none --sparse https://github.com/pytorch/pytorch "$TMP/pt"
cd "$TMP/pt"
git checkout -q "$COMMIT"
git sparse-checkout set --no-cone /CODEOWNERS /AI_POLICY.md /CONTRIBUTING.md /SECURITY.md /LICENSE \
  '/.github/ISSUE_TEMPLATE/' '/.agents/skills/triaging-issues/'
cd - >/dev/null
DEST="$(git rev-parse --show-toplevel)/upstream"
rm -rf "$DEST/CODEOWNERS" "$DEST/AI_POLICY.md" "$DEST/CONTRIBUTING.md" "$DEST/SECURITY.md" "$DEST/LICENSE" "$DEST/github" "$DEST/agents"
cp -r "$TMP/pt/CODEOWNERS" "$TMP/pt/AI_POLICY.md" "$TMP/pt/CONTRIBUTING.md" "$TMP/pt/SECURITY.md" "$TMP/pt/LICENSE" "$DEST/"
cp -r "$TMP/pt/.github" "$DEST/github"
cp -r "$TMP/pt/.agents" "$DEST/agents"
echo "imported pytorch/pytorch@$(git -C "$TMP/pt" rev-parse HEAD) into upstream/ - update the commit in upstream/README.md"
