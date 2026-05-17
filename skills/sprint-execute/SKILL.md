---
name: sprint-execute
description: Executa sprint via spec.md/constraints.md/sprint doc com startup, pre-flight, phased execution, checkpointing, handoff. Modo fix-execution via `--fix <task-id>` consome `.fixes/triage-<task-id>` com probes como gates. Use "/sprint-execute", "/sprint-execute 4", "execute sprint N", "run sprint", "/sprint-execute --fix <task-id>". Aceita número, path, ou --fix. Não use para planejar novo projeto (use project-plan).
metadata:
  version: 1.2.0
  category: project-management
---

# Sprint Execute

When the user invokes /sprint-execute, follow this protocol exactly.

## 1. Session Startup (always, before any code)

0. **Resolve sprint doc** (formatos aceitos: número inteiro `4`, path `sprints/sprint_4.md`, ou `--fix <task-id>`):
   - Número inteiro → `sprints/sprint_<N>.md` (modo sprint forward, fluxo padrão)
   - Path contendo `sprints/` → usar como-está (modo sprint forward)
   - `--fix <task-id>` → `.fixes/triage-<task-id>.md` + `.fixes/triage-<task-id>.json` (modo fix-execution, ver seção 1.1)
   - Sem argumento → ler `.checkpoint.json`, campo `sprint` → resolver como número acima; se `.checkpoint.json` ausente ou campo nulo → listar arquivos em `sprints/` e perguntar ao usuário qual executar
   - Qualquer outro formato → erro explícito: `"Formato inválido. Use: /sprint-execute 4  |  /sprint-execute sprints/sprint_4.md  |  /sprint-execute --fix <task-id>"`
   - Após resolução: confirmar que o arquivo existe em disco; se não → listar diretório apropriado (`sprints/` ou `.fixes/`) e abortar

### Step 0: No-Argument Options

When no argument is passed and `.checkpoint.json` is absent or has no `sprint` field, offer three opções instead of aborting:

```
Nenhum sprint ativo encontrado. Como deseja prosseguir?
  a) Listar sprints disponíveis em sprints/ e selecionar
  b) Informar número ou path do sprint manualmente
  c) Iniciar sessão exploratória sem sprint (STATE plan → confirm com usuário → executar)
```

Wait for user selection before proceeding.

## 1a. Exploration Discipline (Sprint Startup Only)

During Session Startup (section 1 steps 1–5), before writing any code:

- **Limit exploration to 3–4 tool calls** to ground context (read sprint doc, spec.md, checkpoint, handoff). Stop and STATE what you found; do not keep reading indefinitely.
- **STATE the plan explicitly** before any implementation: "I will do X → Y → Z because…" — this surfaces wrong assumptions early.
- **Confirm with user** if the stated plan involves irreversible ops or touches files not mentioned in the sprint doc.

This rule is scoped to sprint startup orientation. It does NOT apply to /diagnose, /catchup, or other skills that require broader exploration by design.

## 1.1 Fix-Execution Mode (when invoked with `--fix <task-id>`)

When `--fix <task-id>` is passed, switch from sprint protocol (phases) to fix-unit protocol (units with explicit prereqs and acceptance probes). Reuses checkpointing/handoff/test-gate machinery; only the source artifact and per-iteration shape differ.

### 1.1.1 Inputs and validation

1. Read `.fixes/triage-<task-id>.json` — fail explicitly if missing: `"Triage ausente. Rode /fix-triage antes."`
2. Read `.fixes/triage-<task-id>.md` for human context (notes, why-now per unit)
3. Validate: every unit must have non-empty `probe` and `expected` fields. If any unit lacks a concrete probe → abort and ask user to re-run /fix-triage on that unit (probe is the gate; without it, /fix-verify cannot work)
4. Record the **pre-fix git ref** in the checkpoint (see 1.1.4) — used later by /fix-verify to compute touched files via `git diff`. If not a git repo, record an empty `touched_files: []` array that each unit will append to.

### 1.1.2 Per-unit execution loop

Iterate `execution_order` from the JSON. For each unit:

1. **State the unit upfront**: id, title, agent, findings addressed, estimate, prereqs declared
2. **Check agent**: if unit's `agent` field is `local` or `codex`, do NOT execute. Mark as `manual_delegate` in checkpoint, log a one-line message (`"U3 (agent=local) — skipped, delegate manually"`), and continue to next unit. Routing decision was made during /fix-triage; sprint-execute does not pause execution to ask. The user reviews the triage artifact before invocation if they want to override.
3. **Run pre-execution prereqs** (only if declared in `prereqs` AND agent is `claude`):
   - `backup` → invoke /backup before any code change (auto-runs, fast)
   - `sanity-check` → invoke /sanity-check; if it returns ADOPT/FORK, pause ONCE — the unit's premise (build new) may no longer hold and human decision is needed. This is the only legitimate mid-execution pause in fix-execution.
4. **Implement the change** to address the unit's findings. Stay scoped to those findings — do NOT opportunistically refactor or fix unrelated issues observed in passing (those go to a follow-up triage).
4. **Run the acceptance probe** (the `probe` field, exact command). Compare output against `expected` — must match quantitatively before proceeding.
   - If probe passes → unit done, write checkpoint, move on
   - If probe fails → STOP. Do not proceed to the next unit. Diagnose, fix, re-run probe. If you can't make it pass within the unit's estimate × 2, mark `escalated` in checkpoint and surface to user.
   - If probe errors (command not found / file missing) → unit's probe is broken, surface to user; do not silently mark passed
5. **Run post-execution prereqs** (only if declared in `post`):
   - `data-audit` → invoke /data-audit on touched dataset
6. **Append touched files** to checkpoint's `touched_files` array (used later by /fix-verify)
7. **Write checkpoint** (see 1.1.4)

### 1.1.3 Scope discipline (critical)

The most common failure in fix-execution is **scope creep**: while fixing finding F1, you notice F8 nearby and "just fix it too". Don't.

- Stay in the unit's declared findings. New issues observed → log them as candidates for the next /fix-triage, do not address inline
- If a finding turns out to be wrong (premise failure — e.g. the bug doesn't reproduce), mark unit `premise-failed` in checkpoint and skip; do NOT invent a new fix mid-unit
- Refactors, comment cleanup, "while we're here" changes → forbidden during fix-execution

### 1.1.4 Checkpointing for fix-execution

Write `.fixes/checkpoint-<task-id>.json` after each unit:

```json
{
  "task_id": "2026-04-28-fnet-fixes",
  "pre_fix_git_ref": "abc123def",
  "units_completed": ["U1", "U2"],
  "unit_in_progress": null,
  "unit_next": "U3",
  "touched_files": ["scrapers/fnet/parser.py", "tests/test_descricao_especie.py"],
  "timestamp": "2026-04-28T14:30:00Z",
  "metrics": {
    "U1": {"probe_result": "12/12 passing", "duration_min": 75},
    "U2": {"probe_result": "0 duplicates", "duration_min": 50}
  }
}
```

If interrupted mid-unit, set `unit_in_progress` and write a `partial_state` describing what was changed but not yet probe-verified.

On resume (`/sprint-execute --fix <task-id>` re-invoked): read this checkpoint, skip units in `units_completed`, resume from `unit_in_progress` (re-run any incomplete steps) or `unit_next`.

### 1.1.5 End of fix-execution

After the last unit's probe passes:

- Update checkpoint with `status: "all-units-complete"`
- **Do NOT call /session-close yet** — `/fix-verify` runs first
- End the session response with: `"Fix-execution complete: <N>/<total> units, todos os probes ✓. Próximo: /fix-verify <task-id>"`

If any unit was escalated or premise-failed:
- End with: `"Fix-execution parcial: <N>/<total> verificados, <M> escalated/premise-failed. Próximo: /fix-verify <task-id> (vai reportar status real); depois decidir re-triage ou aceitar como known issue"`
1. Read the sprint document — confirm goals, deliverables, and acceptance criteria
2. Read `spec.md` and `constraints.md` if present — these are generated by /project-plan and carry project scope, success criteria, and known constraints; treat them as authoritative
3. Read all state files (`.sprint_progress.json`, `last_run.txt`, `handoff_*.md`, `CLAUDE.md`) to ground context from the previous session
4. Read project memory files if present to recover known gotchas, schema definitions, and source-of-truth rules
5. State what you found: current sprint, last completed phase, blockers, pending decisions — before writing a single line of code

### Step 1.4 — Diagnose & Fix Backlog Awareness (G1)

After Session Startup, before Step 1.5:

1. **List active findings:**
   - `.diagnose/findings-*.md` ordered by mtime DESC
   - Load the 3 most recent; skip older (assumed already triaged/archived)
   - For each, extract: target/scope (files or subsystems), findings list with severity (CRÍTICO/ALTO/MÉDIO/BAIXO), timestamp

2. **List pending fix-units:**
   - `.fixes/triage-*.json` ordered by mtime DESC
   - For each, compute status:
     - If `.fixes/checkpoint-<task-id>.json` exists AND `status == "all-units-complete"` AND `.fixes/verify-<task-id>.json` exists AND `safe_to_close == true` → RESOLVED, skip
     - Otherwise → PENDING; load units where `status != verified`

3. **Cross-reference with current sprint scope:**
   - Extract files/subsystems that this sprint will touch (from sprint doc, already read in step 1)
   - For each active finding CRÍTICO/ALTO or pending fix-unit that touches the same files → mark conflict

4. **Decision:**
   - Conflict CRÍTICO or ALTO → **BLOCK**: state `"Sprint N Phase X would touch <file> which has CRÍTICO finding active in <findings-file>:<F>. Resolve before sprint? (recommended) Or continue accepting risk?"` — await human decision. Do NOT proceed silently.
   - Conflict MÉDIO/BAIXO → **ALERT**: state it and continue; record in `.checkpoint.json` field `active_findings`
   - No conflict → continue

5. **Record in `.checkpoint.json`:**
   ```json
   "active_findings": [{"file": "...", "finding_id": "...", "severity": "...", "decision": "block|alert|pass"}],
   "pending_fixes": [{"task_id": "...", "unit_id": "...", "status": "..."}]
   ```

   If project has no `.diagnose/` or `.fixes/` directories → return empty lists silently, no error.

### Step 1.5 — Pre-implementation Gate Query (B.1)

For each PHASE of the sprint to be implemented this session:

1. **Extract topic**: subsystems touched, tools used, proposed approach → generate 2–5 short query strings
   - Example: Phase = "implement descricaoEspecie parser" → queries: `["descricaoEspecie field name", "fnet parser", "schema descricao especie"]`

2. **Execute corpus hierarchy** (stop at first qualifying hit):
   - **Level 2 — CLAUDE.md grep** (default, no infra required):
     `grep -i -B2 -A5 "<query>" CLAUDE.md` for each query; capture matches
   - **Level 3 — ADR.md grep** (if ADR.md exists):
     same pattern
   - **Level 4 — RAG semantic search** (only if Qdrant healthcheck passes within 2s AND project collection exists):
     embed(query) → top-3 chunks with score ≥ threshold_alert; record with numeric score

3. **Apply block/alert criteria:**
   - `max(match_confidence) >= 0.75` OR keyword "NÃO"/"NUNCA" found literally in CLAUDE.md/ADR → **BLOCK**: state `"Gate hit on phase X: <source> says <snippet>. Human confirmation before proceeding?"` — await confirmation. Do NOT proceed to step 2 without decision.
   - `>= 0.60 and < 0.75` → **ALERT**: state `"Gate alert: <source> mentions <snippet>. Proceeding but verify if applicable."` — continue to step 2
   - `< 0.60` or no match → continue silently

4. **Record all gates in `.checkpoint.json`** under field `gates_run`:
   ```json
   [{"phase": "X", "queries": [...], "hits": [...], "decision": "block|alert|pass", "level_used": "grep-fallback|grep|qdrant", "tokens_used": N}]
   ```
   Also write instrumentation to `<project_root>/.gating/metrics-<YYYY-MM-DD>.jsonl` (create dir if missing):
   ```json
   {"ts": "ISO", "phase": "X", "decision": "pass", "level_used": "grep-fallback", "hits": 0}
   ```

**Fallback rule (critical):** If Level 4 fails (Qdrant offline, collection missing, timeout >2s) → fall back to Levels 2–3 with inline warning. NEVER crash. Skill must complete gating in grep-only mode.

**Note (G2):** When writing `.checkpoint.json` (sprint mode), NEVER delete existing `.fixes/checkpoint-*.json` files. They are independent artifacts read by `/catchup` and `/fix-verify`.

## 2. Schema & Source-of-Truth Verification

Before editing any code that touches data:
- Inspect actual schemas via code (`df.columns`, `df.dtypes`, API response dumps) — never assume field names from memory
- Confirm the canonical source hierarchy: processed/ over raw/, live API over cached, fresh reports over CLAUDE.md snapshots
- Check exact field names, folder naming conventions, and encoding requirements documented in CLAUDE.md or SCHEMA.md
- Known critical fields: verify against CLAUDE.md or SCHEMA.md — never assume from memory

## 3. Pre-flight Checklist (auth / environment)

For pipelines with auth or system dependencies, verify before running:
- Azure AD: app registration type, public-client-flow enabled, required scopes (e.g., `Files.ReadWrite.All` not just `Files.ReadWrite`), admin consent granted
- Encoding: confirm `PYTHONIOENCODING=utf-8` or equivalent; Windows Task Scheduler jobs are UTF-8 landmines
- Elevated shell requirements, OneDrive sync residue risks, venv activation
- Catch blockers now — not mid-task

## 4. Execution Protocol

Work in the phases defined in the sprint doc. For each phase:
1. **Backup first** for any destructive or schema-altering operation
2. **Implement the change**
2a. **Gotcha capture (obrigatorio)**: em qualquer turno onde o resultado de um tool foi "esperado X, obteve Y" — antes de qualquer outra acao, append uma linha em `.gotchas-inflight.md`:
    `[HH:MM] CONTEXTO: descricao concisa do gotcha (o que falhou, o que funciona)`
    Nao esperar o session-close. Nao acumular para "escrever depois". Append no mesmo turno.
3. **Run validation immediately** — don't batch validation to the end
4. **State the result quantitatively**: "139/139 tests passing", "704/704 rows, 0 NaN", "56/56 classified, 0 errors" — exit code 0 alone is not sufficient
5. **Write checkpoint** after every completed phase (see below)

Never declare a phase done without a measurable acceptance check.

### Checkpointing (rate-limit resilience)

After each phase completes successfully, write `.checkpoint.json` in the project root:

```json
{
  "sprint": "N",
  "phase_completed": "X",
  "phase_next": "Y",
  "timestamp": "ISO-8601",
  "metrics": { "tests": "139/139", "rows": 704 },
  "state_notes": "brief description of current system state"
}
```

If the session is cut by rate limit or interruption mid-phase, write a partial checkpoint:
```json
{
  "sprint": "N",
  "phase_in_progress": "X",
  "interrupted_at": "brief description of where execution stopped",
  "partial_state": "what was already written/changed before interruption",
  "safe_to_resume": true
}
```

On session resumption, `/catchup` reads this file first — deterministic resume instead of narrative re-explanation.

## 5. Bug Diagnosis Protocol

Before touching code:
1. Reproduce the issue with actual data
2. Verify the premise: confirm the bug is in the code, not stale reports or external artifacts
3. State a hypothesis: "I believe X causes Y because Z"
4. Trace the complete data flow (extractor → filter → scorer → output) if uncertain
5. Fix the root cause, not the symptom

Examples of premise failures to avoid: AGRX11 parser was correct (stale reports misled); RZAG11 delta was a PDF rounding artifact (not a code bug). Read actual output before concluding there is a bug.

## 6. Test & Integrity Gate Rules

- Wire tests into every phase — run after each edit, not just at end
- For data pipelines: compare input vs output counts post-stage; flag mismatches before continuing
- For parsing pipelines: regex-scan outputs for known failure modes (IGNORECASE false positives, null fields, ordering bugs)
- Run pytest with venv python if `venv/` exists; use `--ignore=<path>` to exclude project-local backup folders when present
- Dry-run pipelines before final delivery when side effects are irreversible (email sends, DB writes, API posts)

## 7. Debugging Methodology

- Add diagnostic logging to trace data transformations; read logs before guessing
- For data accumulation bugs: clean-slate iteration (delete wrong data, rerun full window) to validate fix without stale state
- Avoid surface patches — find the invariant that broke
- When a fix requires follow-up work, create a follow-up task explicitly rather than leaving it implicit

## 8. Cross-Session Handoff (end of every sprint or interrupted session)

Before closing, always write/update:
- `handoffs/handoff_sprintN.md`: what was done, what's next, open decisions, known blockers (create `handoffs/` folder if absent)
- State files (`.sprint_progress.json` or equivalent): last completed phase, counters, timestamps
- ADR entries for any architectural decisions made during this sprint
- CLAUDE.md sections for any new gotchas, field names, or environment rules discovered

If the session was interrupted before completion, note explicitly what state the system is in (partial data, half-applied migration, etc.) so the next session can resume safely.

## 9. Model & Autonomy Rules

- **Personal projects**: ONLY recommend local models from the installed Ollama catalog — never suggest Haiku/Sonnet/Opus API
- **Corporate projects**: standard model recommendations apply
- Run autonomously to completion on bundled pre-diagnosed tasks; interrupt only for strategic decisions (scope changes, destructive ops, irreversible actions)
- When edge cases surface mid-sprint, handle pragmatically in a follow-up pass rather than over-specifying upfront

## 10. Project-Specific Rules

For project-specific tool rules (e.g. DuckDB/asof_join, field name gotchas, encoding quirks), see the project's own CLAUDE.md. Skills should remain generic; project-specific reference files live alongside the project, not bundled into the shared skill.
