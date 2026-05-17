---
name: data-audit
description: Runs a full quantitative validation of pipeline output, dataset, or database — count integrity, nulls, schema, dedup, join integrity, encoding, and temporal consistency. Use when user says "/data-audit", "audit the data", "validate pipeline output", "check data quality", "verify row counts", or "pipeline ran but I want to validate results".
metadata:
  version: 1.0.0
  category: data-quality
---

# Data Audit

When the user invokes /data-audit, run a full quantitative validation of a pipeline output, dataset, or database. Never accept "it ran without errors" as a passing result — validate the data itself.

## Mindset

Exit code 0 proves the pipeline didn't crash. It proves nothing about data correctness. Silent data loss, silent duplication, silent coercion, and silent truncation all exit 0. This audit exists to catch what logs miss.

---

## Phase 1 — Establish Baseline

Before running any check, establish what "correct" looks like:

1. **Input count**: how many records entered the pipeline? (source file rows, API records, DB rows before transform)
2. **Expected output count**: should it be equal, filtered-down, or expanded? Document the expected ratio
3. **Critical fields**: which fields must never be null? (e.g., `valor_brl`, `demo_id`, `dataEntrega`)
4. **Known good state**: if a previous run exists, what were its numbers? (704/704, 5.4M situations, 139 tests)
5. **Source of truth**: confirm which directory/table/file is authoritative (`processed/` not `raw/`, live DB not exported CSV)

State the baseline explicitly before running checks. If baseline is unknown, flag it — auditing without a baseline produces unverifiable results.

---

## Phase 2 — Run Checks

Execute each check and record result as PASS / FAIL / WARN with the actual value.

### 2.1 Count Integrity
```
Input rows:          [N]
Output rows:         [N]
Expected ratio:      [1:1 / filtered / expanded]
Dropped rows:        [N] → PASS if 0 or expected, FAIL otherwise
Duplicate rows:      [N] → PASS if 0 or expected, FAIL otherwise
```
For multi-stage pipelines, check count at each stage boundary — loss can happen anywhere.

### 2.2 Null / NaN Audit
For every critical field:
```
[field_name]: [N] nulls / [N] NaN / [N] empty strings → PASS/FAIL
```
- `df[col].isna().sum()` for pandas
- `SELECT COUNT(*) WHERE col IS NULL` for SQL
- Never aggregate these — report per-field

### 2.3 Schema Validation
```
Expected columns present:   PASS/FAIL (list missing)
Unexpected columns:         [list, flag if suspicious]
Dtypes as expected:         PASS/FAIL (list mismatches)
```
Confirm field names match the canonical source (`descricaoEspecie`, not `especieDocumento`). Type coercions (int→float, date→string) must be intentional.

### 2.4 Domain / Range Checks
For numeric fields with known bounds:
```
[field]: min=[X] max=[X] mean=[X] → in expected range? PASS/FAIL
```
Flag: negative values where only positive expected, future dates, zero where zero is invalid, values exceeding known caps.

### 2.5 Deduplication Check
```
Total rows:          [N]
Unique on [key]:     [N]
Duplicates:          [N] → PASS if 0, FAIL/WARN otherwise
```
Identify the dedup key (demo_id, fund ticker + date, document hash). If no dedup key defined, flag it.

### 2.6 Join / Merge Integrity
For any asof_join, merge, or lookup:
```
Left rows before join:   [N]
Right rows matched:      [N]
Unmatched (dropped):     [N] → acceptable? PASS/FAIL/WARN
```
- `asof_join`: verify sort order before and after — silent wrong matches if ordering is wrong
- Left join nulls in right-side columns = unmatched keys, report count
- Inner join row count drop = unmatched keys on both sides, report count

### 2.7 Encoding & Artifact Check
- Scan string fields for: `\x00` null bytes, `?????` replacement chars, `Ã©/Ã£` mojibake, `None` (stringified), `nan` (stringified)
- Check for PDF rounding artifacts in financial fields: values that differ by <0.01 from round numbers (known issue: RZAG11)
- Confirm file encoding if reading from disk (UTF-8 without BOM on Windows pipelines)

### 2.8 Temporal Consistency
For time-series or dated data:
```
Date range:          [min] → [max]
Expected range:      [X] → [Y]
Gaps in sequence:    [N missing periods] → PASS/FAIL
Future dates:        [N] → should be 0
```

### 2.9 Cross-Stage Reconciliation (multi-pipeline)
If data flows through multiple stages (extractor → filter → scorer → DB):
```
Stage 1 output:  [N rows]
Stage 2 input:   [N rows] → match? PASS/FAIL
Stage 2 output:  [N rows]
Stage 3 input:   [N rows] → match? PASS/FAIL
```
Any unexplained drop between stages = data loss. Investigate before proceeding.

---

## Phase 3 — Audit Report

```
## Data Audit: [dataset/pipeline name] — [date]

### Baseline
- Source: [path/table]
- Input: [N] records
- Expected output: [N] records ([ratio logic])
- Previous known-good: [N rows, date]

### Results
| Check               | Result | Value         | Notes              |
|---------------------|--------|---------------|--------------------|
| Count integrity     | PASS   | 704/704       |                    |
| Null audit          | FAIL   | valor_brl: 3  | rows 12, 45, 301   |
| Schema validation   | PASS   | —             |                    |
| Domain/range        | WARN   | min=-0.01     | rounding artifact? |
| Deduplication       | PASS   | 0 dupes       |                    |
| Join integrity      | PASS   | 0 unmatched   |                    |
| Encoding            | PASS   | —             |                    |
| Temporal            | PASS   | 2023-01→2024-12 |                  |

### FAIL / WARN Details
- [check]: [exact rows/values affected] — [likely cause] — [recommended action]

### Verdict
GREEN / YELLOW / RED

GREEN:  all checks PASS — pipeline output is trustworthy
YELLOW: WARNs only — usable but investigate before production use
RED:    any FAIL — do not use this data, investigate root cause first
```

---

## Rules

- Never issue a GREEN verdict if any check is FAIL
- Never skip the baseline phase — unanchored checks produce meaningless numbers
- Report actual values, not just PASS/FAIL — "0 nulls" is more useful than "PASS"
- For financial data: flag rounding artifacts explicitly, do not silently round to match
- For DuckDB: never run audit queries while another process has the file open — results may be stale or locked
- After a RED verdict, do not proceed with downstream tasks until the root cause is found and fixed
