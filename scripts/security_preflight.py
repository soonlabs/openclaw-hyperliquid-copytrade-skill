#!/usr/bin/env python3
"""Pre-release scanner to reduce accidental secret leaks."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv-hl",
    "node_modules",
    "logs",
}

SKIP_FILES = {
    "state.json",
    "runtime-status.json",
    "services-pids.json",
    "tg-offset.json",
    "wallet-analytics.json",
}

ENV_LINE_PATTERNS = [
    ("private-key-var", re.compile(r"^\s*HYPERLIQUID_WALLET_PRIVATE_KEY\s*=\s*(?!\s*$|replace_me|your_|<)", re.IGNORECASE)),
    ("telegram-token-var", re.compile(r"^\s*TELEGRAM_BOT_TOKEN\s*=\s*(?!\s*$|replace_me|your_|<)", re.IGNORECASE)),
    ("executor-bearer-var", re.compile(r"^\s*LIVE_EXECUTOR_BEARER\s*=\s*(?!\s*$|replace_me|your_|<)", re.IGNORECASE)),
]

GENERIC_PATTERNS = [
    ("eth-private-key-like", re.compile(r"\b0x[a-fA-F0-9]{64}\b")),
    ("telegram-bot-token-like", re.compile(r"\b\d{8,}:[A-Za-z0-9_-]{20,}\b")),
]

TEXT_EXT = {".md", ".txt", ".py", ".json", ".yaml", ".yml", ".env", ".example", ".sample", ".sh"}
ENV_LIKE_NAMES = {".env", "env.example", ".env.example", "sample.env"}


def should_scan(path: Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    if path.name in SKIP_FILES:
        return False
    if path.name == ".env":
        return False
    if path.suffix.lower() in TEXT_EXT:
        return True
    if path.name in {"SKILL.md", "SECURITY.md", ".gitignore"}:
        return True
    return False


def iter_files(root: Path):
    for p in root.rglob("*"):
        if p.is_file() and should_scan(p):
            yield p


def main() -> int:
    findings: list[tuple[str, str, int, str]] = []
    for f in iter_files(ROOT):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        name_lower = f.name.lower()
        env_like = (f.suffix.lower() in {".env", ".example", ".sample"}) or (name_lower in ENV_LIKE_NAMES)

        for i, line in enumerate(text.splitlines(), start=1):
            patterns = list(GENERIC_PATTERNS)
            if env_like:
                patterns.extend(ENV_LINE_PATTERNS)
            for tag, pattern in patterns:
                if pattern.search(line):
                    findings.append((str(f.relative_to(ROOT.parent.parent)), tag, i, line[:200]))

    if findings:
        print("❌ Security preflight failed. Potential sensitive content detected:")
        for path, name, ln, snippet in findings:
            print(f"- {path}:{ln} [{name}] {snippet}")
        print("\nPlease remove/rotate secrets before publishing.")
        return 1

    print("✅ Security preflight passed. No obvious secret leaks detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
