---
name: fix-triage
description: Triagem dos findings do /diagnose em fila priorizada de fix-units (1-3h) com probes, agente, prereqs — gera `.fixes/triage-<task-id>.md` consumido por `/sprint-execute --fix`. Use "/fix-triage", "triage these findings", "plan the fixes", "ranquear os achados", "monta o plano de fixes". Não corrige código (só planeja); para feature planning use /sprint-generator.
metadata:
  version: 1.0.0
  category: quality-assurance
---

# Fix Triage

When the user invokes `/fix-triage`, take findings from a prior `/diagnose` and produce a prioritized, executable fix queue. Do not fix anything — only plan and rank.

This skill closes the gap between `/diagnose` (which finds problems) and `/sprint-execute` (which executes work). Without it, fixes get done ad-hoc, lose acceptance criteria, and never get verified.

## 1. Resolve Inputs

Accept the following invocation forms:

- `/fix-triage` (no arg) → look for the most recent diagnose output:
  1. `<projeto>/.diagnose/findings-*.md` (sorted by mtime, newest first)
  2. If none: scan recent conversation context for a `## Diagnóstico:` block produced by `/diagnose`
  3. If neither found: error explicitly — `"Sem findings disponíveis. Rode /diagnose antes."`
- `/fix-triage <path>` → read findings from explicit file path
- Any of the above with flags below

### Flags

- `--severity-min=<critical|high|medium|low>` — drop findings below this severity before ranking. Default: include all.
- `--scope=<subsystem-or-path>` — only triage findings whose evidence touches this path/subsystem. Default: all.
- `--budget=<hours>` — cap the total estimated cost of generated fix-units. Remaining findings go to a `Deferred` section. Default: no cap.

State the resolved input (file path + filters applied) explicitly before proceeding.

## 2. Rank Findings

For each finding, compute three axes:

1. **Severity** — taken from /diagnose output (CRÍTICO / ALTO / MÉDIO / BAIXO)
2. **Blast radius** — how many callers / pipelines / users are affected if this finding fires. High when the finding is in a hot path or shared module; low when isolated.
3. **Dependency** — does fixing finding A unblock or invalidate finding B? Build a small dependency graph. Findings with no incoming deps are candidates to attack first.

Estimate **cost in hours** per finding (granularity: 0.5h, 1h, 2h, 3h). Findings >3h must be split into multiple fix-units.

Output the ranked table:

```
| #  | Finding                    | Sev      | Blast | Deps | Cost | Unit |
|----|----------------------------|----------|-------|------|------|------|
| F1 | descricaoEspecie miss      | CRITICAL | High  | —    | 1.5h | U1   |
| F2 | bare except in fnet auth   | HIGH     | Med   | F1   | 1.0h | U2   |
```

## 3. Decompose into Fix-Units

A fix-unit is the smallest atomic chunk that:
- Has a clear, testable outcome
- Can be executed and verified in one sitting (1–3h)
- Addresses one or more related findings
- Does not depend on a different unit being half-done

If two findings are in the same file, same root cause, and same fix shape — bundle them into one unit. If they touch different subsystems — keep separate.

For each unit, record:

```markdown
### U<N>: <short title> (<estimate>h)
**Findings**: F1, F3
**Why now**: <severity + blast radius rationale>
**Pre-requisites**:
- [ ] /backup — <reason: schema change / bulk overwrite / etc.>
- [ ] /sanity-check — <reason: fix requires building new infra (parser, scraper, etc.)>
- [ ] /fit-evaluator — <reason: route to local/codex/claude>
- [ ] /data-audit (post) — <reason: fix touches data pipeline>
**Acceptance probe**:
\```bash
# concrete command(s) that prove THIS finding is gone
pytest tests/test_descricao_especie.py -v
# expect: 12/12 passing, no skipped
\```
**Dependencies**: U2 (must complete first because <reason>)
**Notes**: <hidden constraints, gotchas from /diagnose>
```

### Acceptance Probe Rules (the most important section)

The probe is the gate. Without a concrete probe, the fix has no exit criterion and `/fix-verify` has nothing to check.

- **Must be executable** — a command, query, grep, or test invocation. Not "verify manually".
- **Must be specific to the finding** — generic `pytest` is not enough; name the test or scope. If no test exists yet, the unit must include "write a test that fails on the bug, then fix".
- **Must have a measurable expected result** — "12/12 passing", "0 rows match", "exit 0 + output contains X", not "looks fine".
- **For silent failures**: probe must include the exact input that previously triggered the silent path, plus assertion that the new path raises/logs/handles correctly.
- **For schema findings**: probe must assert against the live source (API response, actual DataFrame columns), not against a mock.

If you cannot write a concrete probe for a finding, that finding is not ready for triage — flag it as `needs-clarification` in the Deferred section and move on.

## 4. Mark Prerequisites & Resolve Agent

For each unit, evaluate which support skills must run before/after AND decide the agent during triage (not at execution time, to avoid mid-execution pauses):

| Trigger | Action | When |
|---------|--------|------|
| Modifies schema, bulk overwrites, deletes data | declare `/backup` prereq | Before (executed by sprint-execute --fix) |
| Fix requires building new component (parser, scraper, OCR, etc.) | declare `/sanity-check` prereq | Before — may eliminate the unit |
| Non-trivial implementation (>30min) | **invoke `/fit-evaluator` now** during triage | Now — decision frozen into unit |
| Touches data pipeline / produces dataset | declare `/data-audit` post | After (executed by sprint-execute --fix) |

### Agent resolution (during triage, not execution)

For each unit that warrants routing (>30min, or matching local/codex heuristics), invoke `/fit-evaluator` here. Record the result in the unit JSON as `agent: claude|local|codex`. Trivial units (<30min, pure Claude work) can default to `agent: claude` without calling fit-evaluator.

Reason: invoking fit-evaluator during execution causes `/sprint-execute --fix` to pause and surface every non-Claude decision to the user, breaking autonomous execution. Triage time is the right moment for routing decisions — the user reviews the triage artifact before kicking off execution, so non-Claude routing decisions are visible upfront.

`/sprint-execute --fix` then:
- Auto-executes units with `agent: claude`
- Lists units with `agent: local|codex` as `manual_delegate` and skips them (user delegates separately)

Other prereqs (`backup`, `sanity-check`, `data-audit`) are declared as intent only — `/sprint-execute --fix` invokes them when it reaches the unit. They don't pause execution because they're either auto-running (backup) or fast (data-audit), or the unit is paused intentionally (sanity-check found a reuse opportunity → human decision).

## 4.5 Prior-Fix Gate Query (B.2)

After resolving agent (Step 4), before computing execution order, check for duplicate or previously-failed fix attempts:

For each fix-unit proposed in this triage:

1. **Extract signature:**
   ```
   sig = (primary_files_touched, finding_titles, root_cause_keyword)
   ```

2. **Search prior triages in the same project:**
   - List `.fixes/triage-*.json` with mtime within last 30 days (configurable)
   - For each, load units and compare against current unit's signature:
     - Same primary file touched?
     - Finding titles: Jaccard similarity ≥70% over tokens?
   - Record matches

3. **For each match, check verify status:**
   - Read `.fixes/verify-<task-id>.json` if it exists:
     - `status == verified` → prior unit CLOSED the problem → current unit is a **duplicate**: mark `deferred` with `reason: "duplicate of <task-id>:<U-id>"`
     - `status == still-present | premise-failed | escalated` → prior fix FAILED: attach to current unit:
       - `prior_attempt: "<task-id>:<U-id>"`
       - `prior_outcome: "<status>"`
       - `prior_reason: "<texto from verify artifact>"`
       - Add note in unit's `notes` field: `"WARNING: prior attempt <task-id>:<U-id> failed with <status>. Review before re-attempting."`
   - No verify artifact for a matched triage → prior triage was never executed or verified: attach `prior_attempt` metadata with `prior_outcome: "unexecuted"`

4. **This step never blocks** — it enriches units with context and marks duplicates as deferred. Planning continues regardless.

## 5. Compute Execution Order

Topological sort over unit dependencies. Among units with no remaining deps, prefer:
1. Higher severity first
2. Higher blast radius first
3. Lower cost first (quick wins unblock review momentum)

If `--budget` was passed, walk the sorted list summing cost; stop adding units when sum exceeds budget. Move remaining units to `Deferred`.

## 6. Output Artifact

Write to `<projeto>/.fixes/triage-<task-id>.md`. Generate `task-id` as `YYYY-MM-DD-<short-slug>` (slug from the diagnose source or scope, e.g., `2026-04-28-fnet-fixes`).

```markdown
# Fix Triage: <task-id>

## Source
- Diagnose: <path or "inline from session <date>">
- Filters: --severity-min=<X> --scope=<Y> --budget=<Z>
- Generated: <ISO date>

## Ranked Findings
<table from section 2>

## Fix Units
<units from section 3, in execution order>

## Execution Order
1. U1 (no deps)
2. U2 (depends on U1)
3. U3

## Deferred
- F4: <why deferred — out of budget / needs-clarification / blocked on external>
- F7: <why deferred>

## Handoff (for fresh session)
Para retomar do zero:
1. Ler este arquivo
2. Rodar `/sprint-execute --fix <task-id>`
3. Cada unit roda os pre-reqs declarados, implementa, e roda o acceptance probe como gate antes da próxima
4. Ao final: rodar `/fix-verify <task-id>` antes de `/session-close`

Contexto mínimo necessário (sem reler o diagnose inteiro):
- <2-3 linhas resumindo o que está sendo atacado>
- <pointer pra arquivos críticos>
- <gotchas que se aplicam a múltiplas units>
```

Also write `<projeto>/.fixes/triage-<task-id>.json` (machine-readable, used by `/sprint-execute --fix` and `/fix-verify`):

```json
{
  "task_id": "2026-04-28-fnet-fixes",
  "source": ".diagnose/findings-2026-04-28.md",
  "filters": {"severity_min": "high", "scope": "scrapers/fnet", "budget_hours": 4},
  "units": [
    {
      "id": "U1",
      "title": "Fix descricaoEspecie field name",
      "findings": ["F1", "F3"],
      "estimate_hours": 1.5,
      "deps": [],
      "agent": "claude",
      "prereqs": ["backup"],
      "post": [],
      "probe": "pytest tests/test_descricao_especie.py -v",
      "expected": "12/12 passing"
    }
  ],
  "deferred": [{"finding": "F4", "reason": "out of budget"}],
  "execution_order": ["U1", "U2", "U3"]
}
```

## 7. Final Output to User

End with a one-line summary:
```
Triage gerado: <task-id> — <N> units (<total>h), <M> deferred. Próximo: /sprint-execute --fix <task-id>
```

## Rules

- Never fix code during `/fix-triage` — planning only
- Never generate a unit without a concrete acceptance probe
- Never bundle findings from different subsystems into one unit just to reduce count
- Always include the `Deferred` section explicitly — silence implies completeness
- Always write both `.md` (human) and `.json` (machine) artifacts
- If `/diagnose` output has no severity labels, refuse — ask user to re-run /diagnose with proper output format
