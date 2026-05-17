#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scan_internal.py — INTERNAL-FIRST search for /stuck skill.

Scans 7 internal sources for hits matching <component> or <error>:
  1. CLAUDE.md gotchas
  2. memory/adr_decisions.md (project + ~/.claude/projects/<slug>/memory/)
  3. handoffs/handoff_*.md (3 most recent by mtime)
  4. .diagnose/findings-*.md (3 most recent by mtime)
  5. sprints/sprint_*.md (grep DEFER/KNOWN/ARQUITETURAL/OBSOLETO/permanece aberto)
  6. .fixes/triage-*.json (chain detection via `supersedes` field)
  7. git log + _backups/<ts>/ for untracked files

Output: structured JSON to stdout or --output file.
No external deps (stdlib only). Graceful on missing sources.

Usage:
  python scan_internal.py --component <file_or_symbol> --error "<msg>" \
      [--project-root .] [--output .diagnose/stuck-<ts>.json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFER_TOKENS = [
    "DEFER", "KNOWN", "ARQUITETURAL", "OBSOLETO",
    "permanece aberto", "defer", "architectural", "known issue",
    "deferred", "carry-over", "PERMANECE ABERTO",
]


def _read_text_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return ""


def _grep_lines(text: str, needles: list[str], context: int = 2) -> list[dict]:
    """Return list of hits with snippet (line + N context lines)."""
    if not text or not needles:
        return []
    lines = text.splitlines()
    hits: list[dict] = []
    for i, line in enumerate(lines, start=1):
        line_lower = line.lower()
        for needle in needles:
            if not needle:
                continue
            if needle.lower() in line_lower:
                start = max(0, i - 1 - context)
                end = min(len(lines), i + context)
                snippet = "\n".join(lines[start:end])
                hits.append({
                    "line": i,
                    "match": needle,
                    "snippet": snippet[:600],
                })
                break  # 1 hit per line
    return hits


def _scan_claude_md(root: Path, needles: list[str]) -> list[dict]:
    p = root / "CLAUDE.md"
    if not p.exists():
        return []
    text = _read_text_safe(p)
    hits = _grep_lines(text, needles)
    return [{"source": "CLAUDE.md", "location": str(p), **h} for h in hits]


def _scan_adr(root: Path, needles: list[str]) -> list[dict]:
    candidates = [
        root / "memory" / "adr_decisions.md",
        root / "ADR.md",
    ]
    home = Path.home() / ".claude" / "projects"
    if home.exists():
        for sub in home.iterdir():
            adr = sub / "memory" / "adr_decisions.md"
            if adr.exists():
                candidates.append(adr)
    out: list[dict] = []
    for c in candidates:
        if not c.exists():
            continue
        text = _read_text_safe(c)
        hits = _grep_lines(text, needles)
        for h in hits:
            out.append({"source": "ADR", "location": str(c), **h})
    return out


def _top_n_by_mtime(paths: list[Path], n: int) -> list[Path]:
    return sorted([p for p in paths if p.is_file()],
                  key=lambda p: p.stat().st_mtime, reverse=True)[:n]


def _scan_handoffs(root: Path, needles: list[str]) -> list[dict]:
    out: list[dict] = []
    candidates: list[Path] = []
    for pattern in ("handoffs/handoff_*.md", "handoff_sprint_*.md", "handoff_*.md"):
        candidates.extend(root.glob(pattern))
    for p in _top_n_by_mtime(candidates, 3):
        text = _read_text_safe(p)
        hits = _grep_lines(text, needles)
        for h in hits:
            out.append({"source": "handoff", "location": str(p), **h})
    return out


def _scan_diagnose(root: Path, needles: list[str]) -> list[dict]:
    out: list[dict] = []
    diag_dir = root / ".diagnose"
    if not diag_dir.exists():
        return out
    candidates = list(diag_dir.glob("findings-*.md")) + list(diag_dir.glob("red-team-*.md"))
    for p in _top_n_by_mtime(candidates, 3):
        text = _read_text_safe(p)
        hits = _grep_lines(text, needles)
        for h in hits:
            out.append({"source": "diagnose", "location": str(p), **h})
    return out


def _scan_sprints(root: Path, component_needles: list[str]) -> list[dict]:
    """Sprints get TWO scans: (1) component mentions, (2) defer-token mentions.
    Hits where both overlap are STRONG SIGNAL — defer marker on the same component.
    """
    out: list[dict] = []
    sprint_dir = root / "sprints"
    if not sprint_dir.exists():
        return out
    for p in sorted(sprint_dir.glob("sprint_*.md")):
        text = _read_text_safe(p)
        if not text:
            continue
        comp_hits = _grep_lines(text, component_needles)
        defer_hits = _grep_lines(text, DEFER_TOKENS)
        # Strong signal: same line range mentions both
        comp_lines = {h["line"] for h in comp_hits}
        for h in defer_hits:
            # within ±5 lines of any component mention
            if any(abs(h["line"] - cl) <= 5 for cl in comp_lines):
                h["strong"] = True
            out.append({"source": "sprint", "location": str(p), **h})
        # Also include component-only hits as weak signals
        for h in comp_hits:
            out.append({"source": "sprint", "location": str(p), "weak": True, **h})
    return out


def _scan_fixes_chain(root: Path) -> dict:
    """Detect supersedes chain in .fixes/triage-*.json."""
    fixes_dir = root / ".fixes"
    if not fixes_dir.exists():
        return {"chain_detected": False, "chain": []}
    triages = sorted(fixes_dir.glob("triage-*.json"))
    chain: list[dict] = []
    for tp in triages:
        try:
            with tp.open(encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        sup = data.get("supersedes")
        task_id = data.get("task_id", tp.stem)
        if sup:
            chain.append({"task_id": task_id, "supersedes": sup, "file": str(tp)})
    # also check checkpoints for empirical_gate=FAILED
    failed_gates: list[str] = []
    for cp in sorted(fixes_dir.glob("checkpoint-*.json")):
        try:
            with cp.open(encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        metrics = data.get("metrics", {})
        for unit_id, unit_metrics in metrics.items():
            if not isinstance(unit_metrics, dict):
                continue
            gate = unit_metrics.get("empirical_gate", "")
            if isinstance(gate, str) and "FAIL" in gate.upper():
                failed_gates.append(f"{cp.stem}::{unit_id}")
    return {
        "chain_detected": len(chain) >= 1,
        "chain_length": len(chain),
        "chain": chain,
        "empirical_gate_failures": failed_gates,
    }


def _scan_git_and_backups(root: Path, component: str) -> dict:
    """git log -- <component> + _backups/ scan for untracked files."""
    out: dict = {"git_log_count": 0, "git_log_recent": [], "backups_with_file": []}
    if not component:
        return out
    # If component looks like a path, query git
    if "/" in component or component.endswith(".py"):
        try:
            r = subprocess.run(
                ["git", "log", "--oneline", "-n", "10", "--", component],
                capture_output=True, text=True, cwd=str(root), timeout=10,
            )
            if r.returncode == 0 and r.stdout.strip():
                lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
                out["git_log_count"] = len(lines)
                out["git_log_recent"] = lines[:5]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    # Scan _backups/ for matches
    backups_dir = root / "_backups"
    if backups_dir.exists():
        basename = Path(component).name if ("/" in component or "\\" in component) else component
        for sub in sorted(backups_dir.iterdir(), reverse=True)[:10]:
            if not sub.is_dir():
                continue
            # naive: any file with same basename
            for f in sub.rglob("*"):
                if f.is_file() and f.name == basename:
                    out["backups_with_file"].append(str(f))
                    break
    return out


def _build_needles(component: str | None, error: str | None) -> list[str]:
    needles: list[str] = []
    if component:
        needles.append(component)
        # Also use basename as needle if path
        if "/" in component or "\\" in component:
            needles.append(Path(component).name)
        # And symbol-ish parts (e.g. _enable_iterative_calc from _seal_cache.py::_enable_iterative_calc)
        if "::" in component:
            needles.append(component.split("::")[-1])
    if error:
        # Trim long error messages to most-likely-unique phrase
        e = error.strip().strip('"').strip("'")
        if e:
            needles.append(e[:80])
    # Filter empties
    return [n for n in needles if n and len(n) >= 3]


def _recommend_directive(report: dict) -> str | None:
    """Heuristic: what directive does the evidence suggest?"""
    # Strong: any DEFER hit on the component
    for hit in report.get("hits", []):
        if hit.get("strong"):
            return "ACCEPT (defer marker on same component — see strong hit)"
        snippet_l = (hit.get("snippet") or "").lower()
        if any(t.lower() in snippet_l for t in ["defer", "permanece aberto", "arquitetural", "architectural"]):
            return "ACCEPT (defer/architectural marker found)"
    # Chain detected = ABANDON or PIVOT
    chain_info = report.get("chain", {})
    if chain_info.get("chain_detected") and chain_info.get("chain_length", 0) >= 2:
        return "ABANDON (chain >=2 — fix-loop active)"
    if chain_info.get("empirical_gate_failures"):
        return "REVERT (empirical gates failing) or ABANDON path"
    if report.get("hits"):
        return "REVIEW (hits found — manual judgment on form)"
    return None  # internal miss → external search


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Internal-first scan for /stuck skill")
    ap.add_argument("--component", required=True,
                    help="File path, symbol, or component name being investigated")
    ap.add_argument("--error", default="",
                    help="Error message or class string (in quotes)")
    ap.add_argument("--project-root", default=".",
                    help="Project root (default: cwd)")
    ap.add_argument("--output", default="",
                    help="Output JSON path (default: stdout)")
    args = ap.parse_args(argv)

    root = Path(args.project_root).resolve()
    if not root.exists():
        print(f"ERROR: project-root does not exist: {root}", file=sys.stderr)
        return 1

    component_needles = _build_needles(args.component, None)
    full_needles = _build_needles(args.component, args.error)

    report: dict = {
        "scan_timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "project_root": str(root),
        "component": args.component,
        "error": args.error,
        "needles": full_needles,
        "hits": [],
        "chain": {},
        "git_and_backups": {},
        "summary": {},
        "recommended_directive": None,
    }

    # 1+2+3+4 — text grep sources
    report["hits"].extend(_scan_claude_md(root, full_needles))
    report["hits"].extend(_scan_adr(root, full_needles))
    report["hits"].extend(_scan_handoffs(root, full_needles))
    report["hits"].extend(_scan_diagnose(root, full_needles))
    # 5 — sprints (special: combines component + DEFER tokens)
    report["hits"].extend(_scan_sprints(root, component_needles))
    # 6 — chain detection
    report["chain"] = _scan_fixes_chain(root)
    # 7 — git + backups
    report["git_and_backups"] = _scan_git_and_backups(root, args.component)

    # Summary
    report["summary"] = {
        "total_hits": len(report["hits"]),
        "strong_hits": sum(1 for h in report["hits"] if h.get("strong")),
        "weak_hits": sum(1 for h in report["hits"] if h.get("weak")),
        "chain_detected": report["chain"].get("chain_detected", False),
        "chain_length": report["chain"].get("chain_length", 0),
        "empirical_gate_failures": len(report["chain"].get("empirical_gate_failures", [])),
        "git_log_count": report["git_and_backups"].get("git_log_count", 0),
        "backups_with_file": len(report["git_and_backups"].get("backups_with_file", [])),
    }
    report["recommended_directive"] = _recommend_directive(report)

    out_json = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(out_json, encoding="utf-8")
        print(f"OK scan_internal: {report['summary']['total_hits']} hits, "
              f"chain={report['summary']['chain_detected']} (len={report['summary']['chain_length']}); "
              f"output -> {out_path}")
    else:
        print(out_json)

    return 0


if __name__ == "__main__":
    sys.exit(main())
