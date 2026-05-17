#!/usr/bin/env python3
# Snapshot 2026-05-17 — not the canonical copy. Source: ~/.claude/hooks/handoff_vocab_check.py
"""
Stop hook: checks handoff_*.md / HANDOFF.md in cwd for ambiguous vocabulary.
Emits systemMessage WARN via stdout; never blocks (always exit 0).
"""
import sys
import json
import re
import glob
import os

FLAGGED = re.compile(
    r'\b(deployed|ready|done|pronto|deployado)\b',
    re.IGNORECASE
)

# Words that redeem a flagged match when adjacent (within same line)
REDEEMING = re.compile(
    r'\b(built|installed|running|verified|tested|NÃO|NOT)\b',
    re.IGNORECASE
)

TEST_MODE = '--test' in sys.argv


def check_file(path: str) -> list[str]:
    warnings = []
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            for lineno, line in enumerate(f, 1):
                if FLAGGED.search(line) and not REDEEMING.search(line):
                    snippet = line.strip()[:120]
                    warnings.append(f"{path}:{lineno}: {snippet}")
    except OSError:
        pass
    return warnings


def emit_warn(warnings: list[str]) -> None:
    msg = "HANDOFF VOCAB WARN — ambiguous terms found (missing built/installed/running/verified):\n"
    msg += "\n".join(f"  {w}" for w in warnings)
    payload = {"type": "text", "text": msg}
    print(json.dumps(payload), flush=True)


def main() -> None:
    if TEST_MODE:
        # Quick self-test: verify regex works
        assert FLAGGED.search("JAR deployed and ready.")
        assert not FLAGGED.search("no flagged words here.")
        assert REDEEMING.search("built and verified")
        # A line with flagged word AND redeeming word should NOT warn
        line_ok = "JAR v2.1 built at target/app.jar (NOT running)."
        line_bad = "JAR v2.1 deployed and ready."
        assert not (FLAGGED.search(line_ok) and not REDEEMING.search(line_ok)), "false positive on ok line"
        assert FLAGGED.search(line_bad) and not REDEEMING.search(line_bad), "missed bad line"
        print(json.dumps({"type": "text", "text": "handoff_vocab_check --test OK"}), flush=True)
        sys.exit(0)

    # If a specific file was passed (used in probe test), check just that file
    explicit_files = [a for a in sys.argv[1:] if not a.startswith('--')]
    if explicit_files:
        targets = explicit_files
    else:
        cwd = os.getcwd()
        targets = glob.glob(os.path.join(cwd, 'handoff_*.md')) + \
                  glob.glob(os.path.join(cwd, 'HANDOFF.md'))

    if not targets:
        sys.exit(0)

    all_warnings: list[str] = []
    for path in targets:
        all_warnings.extend(check_file(path))

    if all_warnings:
        emit_warn(all_warnings)

    sys.exit(0)


if __name__ == '__main__':
    main()
