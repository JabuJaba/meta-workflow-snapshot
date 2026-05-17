---
name: fix-verify
description: Verifica fixes do /fix-triage — roda probe de cada fix-unit e /diagnose escopado nos touched files, reporta verified/still-present/new-finding. Bloqueia /session-close se restar residuais (--report-only override). Use "/fix-verify", "verify the fixes", "confirma que o fix funcionou", após /sprint-execute --fix. Não corrige (só verifica), exige triage prévia.
metadata:
  version: 1.0.0
  category: quality-assurance
---

# Fix Verify

When the user invokes `/fix-verify`, run the post-execution gate that confirms fixes from a `/fix-triage` actually eliminated the findings — and detects regressions introduced by the fix itself. Do not modify code.

This skill exists because "tests passed" is not the same as "the diagnosed problem is gone". `/fix-verify` is the explicit bridge between executed fixes and a clean session close.

## 1. Resolve Inputs

Accept the following invocation forms:

- `/fix-verify <task-id>` → read `<projeto>/.fixes/triage-<task-id>.json` (machine-readable artifact written by `/fix-triage`)
- `/fix-verify` (no arg) → look for the most recent `.fixes/triage-*.json` (sorted by mtime). If multiple exist, list them and ask which.
- If the JSON artifact is missing: error explicitly — `"Artifact ausente. Rode /fix-triage antes ou passe um task-id válido."`

Also locate the corresponding execution checkpoint (`<projeto>/.fixes/checkpoint-<task-id>.json`, written by `/sprint-execute --fix`) to learn which units were actually executed. Units in the triage but not in the checkpoint are reported as `not-executed`, not as failures.

### Flags

- `--scope=<unit-id|range>` — verify only certain fix-units. Examples: `--scope=U1`, `--scope=U1,U3`, `--scope=units 1-3`. Default: all executed units.
- `--report-only` — generate the report but do NOT block `/session-close`. Default: block when residuals exist.

State the resolved task-id, list of units to verify, and any flags before running anything.

## 2. Run Acceptance Probes

For each fix-unit in scope:

1. Read the unit's `probe` field from the triage JSON (the executable command/check)
2. Read the unit's `expected` field (the measurable expected result)
3. Execute the probe in the project directory
4. Compare actual output against expected:
   - **Pass** → mark unit `verified ✓`
   - **Fail** (probe ran but result differs) → mark unit `still-present ✗`
   - **Probe errored** (command not found, file missing, etc.) → mark unit `probe-broken ⚠` and surface the error

Capture stdout/stderr of each probe — write to `.fixes/verify-<task-id>-probe-<unit>.log` so the user can inspect failures.

Quantitative comparison rules:
- `expected: "12/12 passing"` → match the test summary line; partial like `11/12` is `still-present`
- `expected: "0 rows"` → match exact zero; non-zero is `still-present`
- `expected: "exit 0 + output contains X"` → both conditions must hold
- Free-form expected → at minimum, exit code 0; flag `probe-broken` if expected is too vague to evaluate (acceptance probe should have been concrete)

## 3. Scoped /diagnose on Touched Files

Probes only check the specific findings each unit declared. They do not catch regressions introduced by the fix elsewhere. Run a scoped `/diagnose` to fill that gap.

1. Identify touched files:
   - Prefer `git diff --name-only <pre-fix-ref>..HEAD` if the project is a git repo (use the ref recorded in `checkpoint-<task-id>.json`, or `HEAD~N` where N is the unit count)
   - Fallback: read the `touched_files` array from `checkpoint-<task-id>.json` if present
   - Last resort: re-derive from each unit's notes/probe paths
2. Invoke `/diagnose` with this file list as scope (not the full project)
3. Compare the new findings against the original findings from the triage source:
   - Finding present in original AND in new scoped diagnose → already counted in probe results above
   - Finding NOT in original BUT in new scoped diagnose → `new-finding ⚠` (regression introduced by the fix)
   - Finding in original BUT NOT in new scoped diagnose → consistent with `verified` from probes

Use the original diagnose findings file (`triage-<task-id>.json` → `source` field) as the comparison baseline.

## 4. Output Report

Write `<projeto>/.fixes/verify-<task-id>.md` (human-readable) and `<projeto>/.fixes/verify-<task-id>.json` (machine-readable used by `/session-close`).

### Markdown report

```markdown
# Fix Verify: <task-id>

## Summary
- Units verified: <N>/<total>
- Verified ✓: <count>
- Still-present ✗: <count>
- New findings ⚠: <count>
- Probe-broken ⚠: <count>
- Not-executed: <count>
- **Status**: OK to close / BLOCKED — fix residuals before /session-close

## Per-Unit Results

### U1: <title> — verified ✓
- Probe: `pytest tests/test_descricao_especie.py -v`
- Expected: 12/12 passing
- Actual: 12/12 passing
- Touched files: scrapers/fnet/parser.py, tests/test_descricao_especie.py
- Findings addressed: F1, F3 — confirmed gone via scoped /diagnose

### U2: <title> — still-present ✗
- Probe: `python -m mypipeline.dedup --check`
- Expected: 0 duplicates
- Actual: 7 duplicates
- Log: .fixes/verify-<task-id>-probe-U2.log
- Recommended action: re-open this unit in a follow-up triage

### U3: <title> — new-finding ⚠
- Probe passed (verified the original finding gone)
- BUT scoped /diagnose detected new finding:
  - Category: silent-failure
  - Evidence: `bare except: pass` introduced at scrapers/fnet/auth.py:142
  - Recommended action: address before /session-close, or document explicitly

## Touched Files
- scrapers/fnet/parser.py
- scrapers/fnet/auth.py
- tests/test_descricao_especie.py

## Next Step
- All ✓ → safe to run `/session-close`
- Any ✗ or ⚠ → either fix residuals (re-run `/fix-triage` on residuals + `/sprint-execute --fix` + `/fix-verify`) OR re-run with `--report-only` if you accept the state and will document as known issue
```

### JSON report

```json
{
  "task_id": "2026-04-28-fnet-fixes",
  "verified_at": "2026-04-28T15:30:00Z",
  "safe_to_close": false,
  "summary": {
    "verified": 1,
    "still_present": 1,
    "new_finding": 1,
    "probe_broken": 0,
    "not_executed": 0
  },
  "units": [
    {"id": "U1", "status": "verified", "probe_log": ".fixes/verify-...-probe-U1.log"},
    {"id": "U2", "status": "still_present", "actual": "7 duplicates"},
    {"id": "U3", "status": "new_finding", "regression": "bare except introduced at scrapers/fnet/auth.py:142"}
  ],
  "touched_files": ["scrapers/fnet/parser.py", "scrapers/fnet/auth.py", "tests/test_descricao_especie.py"]
}
```

`safe_to_close` is `true` only if every executed unit is `verified` AND no `new-finding` regressions exist. If `--report-only` was passed, set `safe_to_close: true` and add `"override_reason": "report-only"` so the override is auditable.

## 5. Block or Release

After writing the artifacts:

- If `safe_to_close: false` and `--report-only` was NOT passed:
  - End the response with an explicit instruction: `"BLOCKED: residuals remain. Resolva antes de /session-close, ou rode /fix-verify --report-only se for fechar com known issues."`
  - Do NOT proceed to `/session-close` even if the user types it next — re-run `/fix-verify` first to confirm
- If `safe_to_close: true`:
  - End with: `"OK to close: <N>/<total> units verified. Próximo: /session-close"`

`/session-close` should read `verify-<task-id>.json` if it exists in `.fixes/` and refuse to close when `safe_to_close: false`.

## Rules

- Never modify code during `/fix-verify` — verification only
- Never declare `verified` based on "looks correct" — only the probe's quantitative result counts
- Never skip the scoped /diagnose step (probes don't catch regressions)
- Never override blocking silently — `--report-only` must be explicit and recorded in the JSON
- If a unit's probe is too vague to evaluate (e.g., "tests pass" without scope), flag `probe-broken` rather than guessing — push the failure back to the triage quality
- Always write both `.md` and `.json` artifacts (human + machine consumers)
