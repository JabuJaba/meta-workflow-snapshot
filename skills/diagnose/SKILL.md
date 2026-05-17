---
name: diagnose
description: Red-team review adversarial de código/pipeline/dados/plano/fix — bugs, silent failures, blind spots, omissões. Só diagnostica (não corrige). Grava `.diagnose/findings-<ts>.md` para /fix-triage. Use "/diagnose", "red team this", "find what's wrong", "pente fino", "diagnose before fixing". Não use para fix one-liner.
metadata:
  version: 1.1.0
  category: quality-assurance
---

# Diagnose

When the user invokes /diagnose, run a full adversarial review of the target (code, pipeline, data, plan, or fix). Do not fix anything yet — diagnosis comes first.

## Default scope

If invoked without an explicit target, the target is the current project (cwd) as a whole. Do not ask the user for clarification, do not offer a menu of candidates — proceed directly to Phase 1 with the entire project in scope. Only ask when the cwd is genuinely ambiguous (e.g., a parent directory containing multiple unrelated projects with no clear root).

## Mindset

Act as a red team, not a code reviewer. Assume something is wrong and look for it. Do not stop at the first issue. Work through every category below exhaustively, then synthesize. A clean-looking codebase with silent failures is worse than one with noisy errors.

## Phase 0 — Load Prior Diagnostic State (G3)

Before auditing, build the known-finding registry to avoid re-surfacing already-triaged findings:

1. **Locate prior artifacts:**
   - `.diagnose/findings-*.md` — sort by mtime DESC, load 3 most recent
   - `.fixes/triage-*.{md,json}` — all pending AND last 3 verified
   - `.fixes/verify-*.json` — all

2. **Build known finding registry** (in session memory, not persisted to disk):
   ```
   for each findings_file in recent_findings:
     for each finding in findings_file:
       match_in_triage = search finding.id across triage_files[*].units[*].findings
       if match_in_triage:
         verify_status = lookup verify-<task-id>.json → still_present | verified | new_finding | escalated
       else:
         verify_status = "untriaged"
       known_registry.append({finding_id, file, severity, verify_status, source_diagnose})
   ```

3. If project has no `.diagnose/` or `.fixes/` directories → `known_registry = []`, continue silently

### Sub-step 1.6.0 — Load gotcha anchors for §1.6 (B.3)

Before running the §1.6 negligence check:

1. Load structured entities if present: `config/entities.json`, `config/accounts.json`
2. Extract anchors from `CLAUDE.md` via regex patterns:
   - Heading anchors: `^(##|###)\s*(Gotchas?|Regras?|NÃO|Encoding|Schema)`
   - Inline anchors: lines containing `frágil|antipattern|NUNCA|silent failure`
3. Extract anchors from `ADR.md` (if present) with same patterns
4. Generate **derived findings** for §1.6 from any anchor whose rule is not verifiably applied in the code being audited:
   - Finding format: `[anchor text] — CLAUDE.md line Y / ADR entry Z — [verify whether rule is followed]`
   - Tag these as candidates only; confirm with code evidence before promoting to CRÍTICO/ALTO

---

## Phase 1 — Red Team the Current State

For each category, actively look for evidence. If none found, state "none found" explicitly — don't skip silently.

**Tag every finding emitted with NEW or KNOWN status (G3):**
- Compute fingerprint: severity + file path + 3–5 keywords from the description
- Search `known_registry` (loaded in Phase 0): keyword overlap ≥70% AND same file → tag `KNOWN-<verify_status>` (e.g., `KNOWN-still-present`, `KNOWN-untriaged`, `KNOWN-verified-but-back`)
- No match → tag `NEW`
- `KNOWN-verified-but-back` is a regression signal — flag it explicitly

### 1.1 Bugs (logic errors with incorrect output)
- Trace execution paths with concrete example data
- Check boundary conditions: empty input, single row, max size, nulls
- Verify math, aggregations, date arithmetic
- Confirm join keys, merge conditions, filter predicates

### 1.2 Silent Failures (succeed but produce wrong results)
These are the most dangerous. Look for:
- Functions that return success even on bad input (bare `except: pass`, `|| true`)
- Filters that silently match too broadly or too narrowly (regex with IGNORECASE on structured data)
- Joins that silently drop or duplicate rows (asof_join ordering, unmatched keys)
- Encoders/parsers that silently coerce bad values (NaN→0, None→"None", rounding artifacts)
- Writes that silently overwrite instead of append (or vice versa)
- API responses that return 200 with an error payload inside

### 1.3 Blind Spots (assumptions never verified)
- Schema assumptions: are field names confirmed against actual API/DB response? (`descricaoEspecie` vs `especieDocumento`)
- Source-of-truth assumption: is this reading from processed/ or raw/? From live API or stale cache?
- Volume assumption: tested on 10 rows, will it hold at 700K?
- Encoding assumption: UTF-8 confirmed, or assumed? (Windows Task Scheduler, OneDrive sync)
- Concurrency assumption: safe to run twice simultaneously? (DuckDB file locks, in-memory dedup)
- Date/timezone assumption: timestamps localized or naive?

### 1.4 Omissions (missing logic that should exist)
- Missing validation at system boundaries (user input, API responses, file reads)
- Missing idempotency guard (what happens if this runs twice?)
- Missing rollback path for destructive operations
- Missing test coverage for the changed path
- Missing dedup logic where duplicates are possible
- Missing encoding declaration (open() without encoding=)

### 1.5 Underestimations (scope or complexity understated)
- "Simple change" that touches a hot path used by many callers
- "Quick fix" that requires schema migration or data backfill
- "Minor refactor" that breaks serialization of existing state files
- Performance: O(n²) loop on a dataset that will grow
- External dependency assumed stable (API rate limits, PDF format changes, OneDrive latency)

### 1.6 Negligences (known gotchas not applied)
- Project-specific rules from CLAUDE.md not followed
- Known field name traps not checked
- Standard pre-flight skipped (auth verification, venv activation, encoding setup)
- Test suite not run after change
- Dry-run skipped before irreversible side effect
- Backup not taken before destructive operation

---

## Phase 2 — Anticipate Subsequent Errors from Proposed Fixes

For each fix or improvement identified in Phase 1 (or proposed by the user), run a second-order analysis:

For every fix, ask:
1. **What does this fix assume that could also be wrong?** (fixing the wrong layer, wrong root cause)
2. **What does this change break downstream?** (callers, dependent pipelines, serialized state)
3. **Does this fix introduce a new silent failure mode?** (e.g., stricter validation that silently drops valid edge cases)
4. **Is the fix reversible?** If not, what is the rollback plan?
5. **Does this fix need a test to prevent regression?** What input would catch it?

State these risks explicitly. Don't assume the fix is safe because it looks correct in isolation.

---

## Phase 3 — Prioritized Finding Report

Output findings in this structure (G3: NEW/KNOWN sub-sections within each severity level):

```
## Diagnóstico: [target name]

### CRÍTICO (bloqueia ou corrompe dados)

#### NEW (not seen in prior diagnose)
- [finding] [TAG=NEW] — [evidence] — [recommended action]

#### KNOWN (previously documented)
- [finding] [TAG=KNOWN-untriaged|KNOWN-still-present|KNOWN-verified-but-back] — [evidence] — [recommended action]
  Pointer: <findings-file>:<F-id> | <triage-task-id>:<U-id> | <verify-task-id>

### ALTO (falha silenciosa ou perda de dados provável)

#### NEW
- [finding] [TAG=NEW] — [evidence] — [recommended action]

#### KNOWN
- [finding] [TAG=KNOWN-*] — [evidence] — [recommended action]
  Pointer: <source>

### MÉDIO (omissão ou premissa não verificada)

#### NEW
- ...

#### KNOWN
- ...

### BAIXO (negligência ou underestimation)

#### NEW
- ...

#### KNOWN
- ...

### Riscos Secundários das Correções Propostas
- Fix [X] → risco: [Y] — mitigação: [Z]

### Não encontrado
- [categories where no issues were found, listed explicitly]
```

Rules for NEW/KNOWN tagging:
- If `known_registry` is empty (no prior diagnose artifacts), ALL findings are tagged NEW
- Omit empty sub-sections (e.g., if no KNOWN findings at CRÍTICO level, omit "#### KNOWN")
- `KNOWN-verified-but-back` is a regression — always call it out explicitly even if severity seems lower
- Always include the "Não encontrado" section — absence of findings must be stated, not implied

---

## Phase 4 — Persist Artifact

After emitting the report in the response, also write it to disk so downstream skills (`/fix-triage`) can consume it in a fresh session without losing context.

1. Create `<projeto>/.diagnose/` if missing
2. Write the full report to `<projeto>/.diagnose/findings-<timestamp>.md` where timestamp is `YYYY-MM-DD-HHMMSS` (sortable, conflict-free for multiple runs in a day)
3. Include in the file header:
   - `target`: what was diagnosed (file/path/component)
   - `scope`: which subsystem/files were in-scope for this diagnose
   - `generated`: ISO timestamp
4. End the response with a one-line pointer: `"Findings persisted: .diagnose/findings-<timestamp>.md — próximo (opcional): /fix-triage"`

Skip persistence only if the diagnose target is conceptual/abstract (a plan being reviewed, not a codebase) and there's no project directory to write into. State the skip explicitly.

---

## Rules

- Never skip a category because the code "looks clean"
- Never conflate "no test failed" with "no bug exists"
- State the severity of each finding — don't bury a data corruption bug under style notes
- If you lack visibility into a dependency (external API, file produced by another pipeline), flag it as an unverified assumption rather than assuming it's fine
- Do not implement fixes during /diagnose — produce findings only, let the user decide what to fix and in what order
