# Snapshot 2026-05-17 — not the canonical copy. Source: ~/.claude/hooks/injection_guard.py
"""
PreToolUse hook — barreira de segurança global.

Bloqueia:
1. Chamadas Bash a learn.py com conteúdo suspeito (injeção via learnings pipeline).
2. Ferramentas MCP destrutivas (LinkedIn, Supabase, Microsoft 365, Box, Notion, Asana).

Protocolo Claude Code:
  exit 0  → permitir
  exit 2  → bloquear (decisão intencional, não erro)
  stdout  → JSON com {"decision": "block", "reason": "..."}  quando bloqueando
"""
import sys
import json
import re
import os
from pathlib import Path

sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
sys.stderr = open(sys.stderr.fileno(), mode="w", encoding="utf-8", buffering=1)

SECURITY_LOG = Path.home() / ".claude" / "security.log"

# ---------------------------------------------------------------------------
# Padrões de injeção em argumentos de Bash
# ---------------------------------------------------------------------------
_INJECTION_PATTERNS = re.compile(
    r"(ignore\s+(previous|prior|all)\s+(instructions?|rules?|context)"
    r"|instrução\s+prioritária"
    r"|system\s+override"
    r"|forget\s+(your|all)\s+(instructions?|rules?)"
    r"|new\s+persona"
    r"|you\s+are\s+now\s+a"
    r"|\bDAN\b"
    r"|jailbreak"
    r"|IGNORE\s+ALL"
    r"|disregard\s+(all|previous))",
    re.IGNORECASE,
)

_HEADING_PATTERN = re.compile(r"(?:^|\s)#{1,6}\s")

MAX_LEARN_ARG_LEN = 350  # um pouco acima do limite do learn.py para capturar tentativas

# ---------------------------------------------------------------------------
# MCPs destrutivos — ferramentas que modificam estado externo irreversivelmente
# ---------------------------------------------------------------------------
DESTRUCTIVE_MCP_TOOLS = {
    # LinkedIn
    "mcp__linkedin__linkedin_create_post",
    "mcp__linkedin__linkedin_delete_post",
    "mcp__linkedin__linkedin_update_post",
    "mcp__linkedin__linkedin_create_comment",
    "mcp__linkedin__linkedin_delete_comment",
    # Microsoft 365
    "mcp__microsoft_365__send_email",
    "mcp__microsoft_365__send_mail",
    "mcp__microsoft_365__delete_email",
    "mcp__microsoft_365__delete_file",
    "mcp__microsoft_365__move_file",
    "mcp__microsoft_365__create_event",
    "mcp__microsoft_365__delete_event",
    "mcp__microsoft_365__update_event",
    # Supabase — qualquer operação de escrita
    "mcp__supabase__execute_sql",
    "mcp__supabase__insert_row",
    "mcp__supabase__update_row",
    "mcp__supabase__delete_row",
    "mcp__supabase__run_query",
    # Box
    "mcp__box__delete_file",
    "mcp__box__upload_file",
    "mcp__box__move_file",
    "mcp__box__create_folder",
    "mcp__box__delete_folder",
    # Notion
    "mcp__notion__create_page",
    "mcp__notion__update_page",
    "mcp__notion__delete_page",
    "mcp__notion__create_database",
    "mcp__notion__update_database",
    # Asana
    "mcp__asana__create_task",
    "mcp__asana__update_task",
    "mcp__asana__delete_task",
    "mcp__asana__create_project",
    # HubSpot
    "mcp__hubspot__create_contact",
    "mcp__hubspot__update_contact",
    "mcp__hubspot__delete_contact",
    "mcp__hubspot__send_email",
    # Vercel
    "mcp__vercel__deploy",
    "mcp__vercel__delete_deployment",
    "mcp__vercel__delete_project",
    # Monday.com
    "mcp__monday_com__create_item",
    "mcp__monday_com__update_item",
    "mcp__monday_com__delete_item",
}


def _log(msg: str) -> None:
    try:
        with open(SECURITY_LOG, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except OSError:
        pass


def _block(reason: str, tool: str) -> None:
    payload = json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False)
    print(payload)
    _log(f"BLOCKED tool={tool} reason={reason}")
    sys.exit(2)


def _allow() -> None:
    sys.exit(0)


try:
    hook_data = json.load(sys.stdin)
except (json.JSONDecodeError, EOFError):
    # Sem dados de entrada — permitir (não bloquear por erro de hook)
    sys.exit(0)

tool_name = hook_data.get("tool_name", "")
tool_input = hook_data.get("tool_input", {})

# ---------------------------------------------------------------------------
# Verificação 1: Bash calls suspeitas ao pipeline de learnings
# ---------------------------------------------------------------------------
if tool_name == "Bash":
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""

    if "learn.py" in command:
        # Só inspecionar quando learn.py é o script principal sendo executado
        # (python ... learn.py <categoria> <conteudo>), não quando aparece como
        # argumento de outro comando (py_compile, ruff, cat, etc.)
        args_match = re.search(r"learn\.py\s+(\w+)\s+(.*)", command, re.DOTALL)
        if args_match:
            learn_args = args_match.group(2).strip()

            if len(learn_args) > MAX_LEARN_ARG_LEN:
                _block(
                    f"Argumento de learn.py excede {MAX_LEARN_ARG_LEN} chars — possível injeção por volume.",
                    tool_name,
                )

            if _HEADING_PATTERN.search(learn_args):
                _block(
                    "Argumento de learn.py contém heading markdown — possível injeção de contexto.",
                    tool_name,
                )

            if _INJECTION_PATTERNS.search(learn_args):
                _block(
                    "Argumento de learn.py contém padrão de injeção de instrução.",
                    tool_name,
                )

    # Bloquear chamadas Python com URL como argumento (possível exfiltração)
    if re.search(r"python[3]?\s+.*https?://", command):
        _block(
            "Chamada Python com URL como argumento — possível exfiltração ou download remoto.",
            tool_name,
        )

# ---------------------------------------------------------------------------
# Verificação 2: MCPs destrutivos
# ---------------------------------------------------------------------------
if tool_name in DESTRUCTIVE_MCP_TOOLS:
    _block(
        f"Ferramenta MCP destrutiva bloqueada: {tool_name}. "
        f"Para executar, confirme explicitamente na próxima mensagem: CONFIRMO {tool_name}",
        tool_name,
    )

_allow()
