# Snapshot 2026-05-17 — not the canonical copy. Source: ~/.claude/hooks/auto_learn_from_claude_md.py
"""
PostToolUse hook: quando Edit ou Write toca CLAUDE.md, extrai o novo conteudo
e grava em pending_learnings.jsonl para ingestao no Stop hook.

Categorias inferidas pelo conteudo:
  gotcha     — linhas com NÃO / NUNCA / SEMPRE / bloqueado / falha
  correction — linhas que corrigem algo (confirmado / errado / fix)
  decision   — linhas com ADR / decidido / escolhido / estrategia
  rule       — linhas com obrigatorio / obrigatório / regra / proibido
  context    — tudo que nao se encaixa acima
"""
import sys
import json
import re
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
sys.stderr = open(sys.stderr.fileno(), mode="w", encoding="utf-8", buffering=1)

# Telemetry path injection (graceful fail)
_HOOK_DIR = str(Path(__file__).parent)
if _HOOK_DIR not in sys.path:
    sys.path.insert(0, _HOOK_DIR)

PENDING = Path.home() / ".claude" / "pending_learnings.jsonl"
MAX_CONTENT = 280  # chars por entry, respeitando limite do learn.py

GOTCHA_RE = re.compile(r"\b(não|nao|nunca|sempre|bloqueado|bloqueia|falha|confirmado|rejeitado|proibido)\b", re.I)
CORRECTION_RE = re.compile(r"\b(corrigido|fix|erro|errado|wrong|obsoleto|substituído|substituido)\b", re.I)
DECISION_RE = re.compile(r"\b(ADR|decidido|decidimos|escolhido|estrategia|estratégia|pivot)\b", re.I)
RULE_RE = re.compile(r"\b(obrigatorio|obrigatório|regra|NUNCA|SEMPRE|proibido|CRITICAL)\b", re.I)


def infer_category(text: str) -> str:
    if RULE_RE.search(text):
        return "rule"
    if GOTCHA_RE.search(text):
        return "gotcha"
    if CORRECTION_RE.search(text):
        return "correction"
    if DECISION_RE.search(text):
        return "decision"
    return "context"


def project_name(project_path: str) -> str:
    if not project_path:
        return "unknown"
    parts = Path(project_path.replace("\\", "/")).parts
    for i, part in enumerate(parts):
        if part.lower() in ("ai_lab", "ai lab") and i + 1 < len(parts):
            return parts[i + 1]
    return parts[-1] if parts else "unknown"


def extract_lines(new_string: str) -> list[str]:
    lines = []
    for line in new_string.splitlines():
        line = line.strip()
        # Pular linhas vazias, headers markdown puras, e comentarios
        if not line or line.startswith("#") and len(line.split()) <= 2:
            continue
        if line.startswith("---") or line.startswith("==="):
            continue
        # So bullet points e linhas com conteudo substantivo
        if line.startswith("-") or line.startswith("*") or len(line) > 40:
            lines.append(line[:MAX_CONTENT])
    return lines


try:
    hook_data = json.load(sys.stdin)

    tool_name = hook_data.get("tool_name", "")
    if tool_name not in ("Edit", "Write"):
        sys.exit(0)

    tool_input = hook_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    # Apenas para CLAUDE.md (local ou global)
    if not file_path.endswith("CLAUDE.md"):
        sys.exit(0)

    # Para Edit: captura new_string. Para Write: captura content inteiro (mas so as linhas novas seria ideal)
    if tool_name == "Edit":
        new_content = tool_input.get("new_string", "")
    else:
        # Write: pega todo o conteudo — pode ser muito. Pegar so as ultimas 30 linhas.
        content = tool_input.get("content", "")
        new_content = "\n".join(content.splitlines()[-30:])

    lines = extract_lines(new_content)
    if not lines:
        sys.exit(0)

    project_path = hook_data.get("project_path", "")
    proj = project_name(project_path)
    now = datetime.now(timezone.utc).isoformat()

    entries = []
    # Cap em 25 (era 5; subiu pos-sanity-check 2026-05-10 — gotchas multi-linha como JCEF doc precisam capturar mais do que 5 linhas).
    # extract_lines() ja filtra (pula vazias/headers) e truncate por-linha em MAX_CONTENT (280 chars) — cap aqui e contra flood em massive Write ops.
    for line in lines[:25]:
        category = infer_category(line)
        entries.append({
            "project": proj,
            "category": category,
            "content": line,
            "logged_at": now,
            "source": "auto_learn_claude_md"
        })

    if not entries:
        sys.exit(0)

    with open(PENDING, "a", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"[auto_learn] {len(entries)} learnings queued from CLAUDE.md edit ({proj})")

    # Telemetry emit (no-op if backend not running)
    try:
        from _hook_telemetry import emit_hook_fire
        emit_hook_fire(hook_event="PostToolUse", hook_name="auto_learn", tool=tool_name, project=proj, learnings_count=str(len(entries)))
    except Exception:
        pass

except Exception as e:
    print(f"[auto_learn error] {e}", file=sys.stderr)
    sys.exit(0)
