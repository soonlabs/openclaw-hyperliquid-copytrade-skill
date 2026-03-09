#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
HOOKS_DIR="$REPO_ROOT/.githooks"
HOOK_FILE="$HOOKS_DIR/pre-commit"

mkdir -p "$HOOKS_DIR"
cat > "$HOOK_FILE" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
python3 skills/openclaw-hyperliquid-copytrade/scripts/security_preflight.py
EOF
chmod +x "$HOOK_FILE"

git -C "$REPO_ROOT" config core.hooksPath .githooks

echo "✅ Installed pre-commit hook at $HOOK_FILE"
echo "✅ Git hooksPath set to .githooks"
