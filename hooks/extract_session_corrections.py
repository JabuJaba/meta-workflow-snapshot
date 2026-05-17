# Snapshot 2026-05-17 — not the canonical copy. Source: ~/.claude/hooks/extract_session_corrections.py
"""Stop hook — extrai correções do user no transcript da sessão recém-fechada.

Sinal: user dizendo em texto "voce errou", "ja falei", "de novo", "isso nao", etc.
Esses sinais NÃO são tool_failures (tools tecnicamente succeeded) mas são exatamente
a dor "preciso interromper 5-6x falando o mesmo erro".

Grava em ~/.claude/learnings.db tabela user_corrections.
Spec: handoff_2026-05-10 PARTE 4 Bloco 2 Phase 1 + Phase 6 (extractor é o data source
de attempts[].failure_mode que o plano deixou unspecified).

Graceful fail — nunca bloqueia Stop.
"""

import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', buffering=1)

# DB stays in ~/.claude/ (shared between cl + clm — continuous learning).
# Transcript/projects respect CLAUDE_CONFIG_DIR so each session reads its own.
DB = os.path.expanduser('~/.claude/learnings.db')
_CFG = os.environ.get('CLAUDE_CONFIG_DIR') or str(Path.home() / ".claude")
PROJECTS_DIR = Path(_CFG) / 'projects'

# Empirically validated against a sample of recent session transcripts
PATTERNS = [
    r"\b(j[áa] (te |)falei|de novo|outra vez|mais uma vez|errou de novo|esqueceu|insist[ie]|repetindo)\b",
    r"\b(n[ãa]o (era|[ée])|isso n[ãa]o|t[áa] errado|est[áa] errado|incorreto)\b",
    r"\b(pare|parou) (tudo|de|com|aqui|agora|um)\b",
    r"\b(pesquise melhor|busque|procure melhor|esqueceu (do |a |o )?processo)\b",
    r"\b(reativ[oa]|atalho|improvis[oa]|foge do processo)\b",
    r"\b(\d+ ?x (j[áa] |)(falei|disse|repeti|pedi|avisei|expliquei|mandei|corrigi)|(j[áa] |)(falei|disse|repeti|pedi|avisei) (isso |o mesmo |de novo )?\d+ ?(x|vez)|5-6|v[áa]rias vezes)\b",
]
COMBINED = re.compile("|".join(PATTERNS), re.IGNORECASE)

MAX_SNIPPET = 400
MAX_PER_SESSION = 20  # cap pra não floodar DB se sessão for um desabafo só


def _project_name(cwd_or_path: str) -> str:
    if not cwd_or_path:
        return ""
    parts = Path(cwd_or_path.replace("\\", "/")).parts
    for i, p in enumerate(parts):
        if p.lower() in ("ai_lab", "ai lab") and i + 1 < len(parts):
            return parts[i + 1]
    return parts[-1] if parts else ""


def _find_transcript(session_id: str, transcript_path: str = "") -> Path | None:
    if transcript_path:
        p = Path(transcript_path)
        if p.exists():
            return p
    # Search across all project dirs
    for proj_dir in PROJECTS_DIR.iterdir() if PROJECTS_DIR.exists() else []:
        candidate = proj_dir / f"{session_id}.jsonl"
        if candidate.exists():
            return candidate
    return None


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict):
                if c.get("type") == "text":
                    parts.append(c.get("text", ""))
                elif c.get("type") == "tool_use":
                    parts.append(f"[tool_use:{c.get('name','?')}]")
        return " ".join(parts)
    return str(content)


def _summarize_action(text: str) -> str:
    """Compact 1-line summary of the preceding assistant turn."""
    if not text:
        return ""
    text = text.strip()
    # Pull tool_use markers if present
    tools = re.findall(r"\[tool_use:(\w+)\]", text)
    snippet = re.sub(r"\[tool_use:\w+\]", "", text).strip()[:200]
    snippet = re.sub(r"\s+", " ", snippet)
    if tools:
        return f"({'+'.join(tools[:3])}) {snippet}"[:240]
    return snippet[:240]


def _scan_transcript(path: Path):
    """Iterate user messages, return list of (user_text, preceding_action, pattern)."""
    hits = []
    prev_assistant_text = ""
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                try:
                    j = json.loads(line)
                except json.JSONDecodeError:
                    continue
                role_type = j.get("type")
                if role_type == "assistant":
                    msg = j.get("message", {})
                    prev_assistant_text = _extract_text(msg.get("content", ""))
                elif role_type == "user":
                    msg = j.get("message", {})
                    text = _extract_text(msg.get("content", ""))
                    text = text.strip()
                    # Skip tool_result-only messages and very long pastes
                    if not text or len(text) > 4000:
                        continue
                    # Skip system-injected blocks (system-reminders, hook output)
                    if text.startswith("<") and ">" in text[:200] and "system" in text[:200].lower():
                        continue
                    m = COMBINED.search(text)
                    if m:
                        hits.append((text[:MAX_SNIPPET], _summarize_action(prev_assistant_text), m.group(0)))
                        if len(hits) >= MAX_PER_SESSION:
                            break
    except Exception:
        pass
    return hits


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    session_id = data.get("session_id", "") or ""
    cwd = data.get("cwd") or data.get("project_path") or ""
    transcript_path = data.get("transcript_path", "")

    if not session_id:
        sys.exit(0)

    tx = _find_transcript(session_id, transcript_path)
    if not tx:
        sys.exit(0)

    project = _project_name(cwd) or _project_name(str(tx.parent.name).replace("--", "/"))
    hits = _scan_transcript(tx)

    if not hits:
        sys.exit(0)

    try:
        c = sqlite3.connect(DB, timeout=2)
        # Avoid duplicates if Stop fires twice on same session
        c.execute("DELETE FROM user_corrections WHERE session_id = ?", (session_id,))
        now = datetime.now(timezone.utc).isoformat()
        c.executemany(
            "INSERT INTO user_corrections (session_id, project, cwd, user_text, preceding_action, pattern_matched, logged_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(session_id, project, cwd, u, a, p, now) for u, a, p in hits],
        )
        c.commit()
        c.close()
        print(f"[extract_session_corrections] {project} — {len(hits)} corrections capturadas")
    except Exception as e:
        print(f"[extract_session_corrections error] {e}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
