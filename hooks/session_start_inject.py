# Snapshot 2026-05-17 — not the canonical copy. Source: ~/.claude/hooks/session_start_inject.py
import sys
import json
import sqlite3
from pathlib import Path
from collections import defaultdict

sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
sys.stderr = open(sys.stderr.fileno(), mode="w", encoding="utf-8", buffering=1)

# Telemetry path injection (graceful fail — see _hook_telemetry.py)
_HOOK_DIR = str(Path(__file__).parent)
if _HOOK_DIR not in sys.path:
    sys.path.insert(0, _HOOK_DIR)

CLAUDE_DIR = Path.home() / ".claude"
DB_PATH = CLAUDE_DIR / "learnings.db"

MAX_LEARNINGS = 25
MAX_CORRECTIONS = 3
CORRECTIONS_WINDOW_DAYS = 14
# Categorias em ordem de importância para exibição
CATEGORY_ORDER = ["rule", "decision", "interface", "correction", "gotcha", "context"]
CATEGORY_LABELS = {
    "rule":       "Regras",
    "decision":   "Decisoes arquiteturais",
    "interface":  "Contratos de interface",
    "correction": "Correcoes documentadas",
    "gotcha":     "Gotchas",
    "context":    "Contexto de sprint",
}


def project_name(project_path: str) -> str:
    if not project_path:
        return ""
    parts = Path(project_path.replace("\\", "/")).parts
    for i, part in enumerate(parts):
        if part.lower() in ("ai_lab", "ai lab") and i + 1 < len(parts):
            return parts[i + 1]
    return parts[-1] if parts else ""


try:
    hook_data = json.load(sys.stdin)
    project_path = hook_data.get("project_path", "")
    proj = project_name(project_path)

    if not proj or not DB_PATH.exists():
        sys.exit(0)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Learnings do projeto atual, mais recentes primeiro
    rows = conn.execute(
        """
        SELECT category, content, logged_at
        FROM learnings
        WHERE project = ?
        ORDER BY logged_at DESC
        LIMIT ?
        """,
        (proj, MAX_LEARNINGS),
    ).fetchall()

    # User corrections do mesmo projeto, janela de 14 dias
    correction_rows = conn.execute(
        """
        SELECT user_text, preceding_action, logged_at
        FROM user_corrections
        WHERE project = ?
          AND logged_at >= datetime('now', ?)
        ORDER BY logged_at DESC
        LIMIT ?
        """,
        (proj, f'-{CORRECTIONS_WINDOW_DAYS} days', MAX_CORRECTIONS),
    ).fetchall() if conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='user_corrections'"
    ).fetchone() else []

    conn.close()

    if not rows and not correction_rows:
        sys.exit(0)

    # Agrupar por categoria
    by_cat = defaultdict(list)
    for row in rows:
        by_cat[row["category"]].append(row["content"])

    lines = []

    # User corrections PRIMEIRO (alta prioridade — atacar a dor "esqueceu que eu falei")
    if correction_rows:
        lines.append(f"<user-corrections project=\"{proj}\" count=\"{len(correction_rows)}\" window_days=\"{CORRECTIONS_WINDOW_DAYS}\">")
        lines.append("<!-- Padroes recorrentes neste projeto -- aprenda sem pedir permissao por causa disto. -->")
        for cr in correction_rows:
            user_snippet = (cr["user_text"] or "")[:300].replace("\n", " ")
            action = (cr["preceding_action"] or "")[:160].replace("\n", " ")
            date = (cr["logged_at"] or "")[:10]
            lines.append(f"- [{date}] {user_snippet}")
            if action:
                lines.append(f"    (contexto anterior: {action})")
        lines.append("</user-corrections>")
        lines.append("")

    if rows:
        lines.append(f"<learnings project=\"{proj}\" count=\"{len(rows)}\">")
        for cat in CATEGORY_ORDER:
            if cat not in by_cat:
                continue
            label = CATEGORY_LABELS.get(cat, cat)
            lines.append(f"<!-- {label} -->")
            for item in by_cat[cat]:
                lines.append(f"- {item}")
            lines.append("")
        lines.append("</learnings>")

    output = "\n".join(lines)
    print(output)
    print(f"[session_start_inject] {proj} - {len(rows)} learnings + {len(correction_rows)} corrections injetados", file=sys.stderr)

    # Telemetry emit (no-op if backend not running — see _hook_telemetry.README.md)
    try:
        from _hook_telemetry import emit_hook_fire, emit_memory_inject
        emit_hook_fire(hook_event="SessionStart", hook_name="session_start_inject", project=proj)
        emit_memory_inject(source="learnings_db", bytes_count=len(output), count=len(rows), project=proj)
    except Exception:
        pass

except Exception as e:
    print(f"[session_start_inject error] {e}", file=sys.stderr)
    sys.exit(0)
