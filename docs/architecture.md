# Architecture — Two Loops

The workflow is built around two distinct loops that share state through a small set of file conventions.

## Forward loop (planned work)

```
  project-plan
       ↓
  spec.md, constraints.md
       ↓
  sprint-generator
       ↓
  sprints/sprint_NN_<theme>.md
       ↓
  sprint-execute
       ↓
  Phase 0 (anchor read) → Phase 1 → Phase 2 → ... → Phase N
       ↓                                              ↓
  .checkpoint.json (rate-limit resilience)      handoffs/handoff_sprint_NN.md
```

The forward loop is what drives planned, scoped work. Each step produces an artifact consumed by the next step. The loop is **stateful**: `.checkpoint.json` allows resumption after interruption (rate limits, session ends, machine restart) without re-explanation in prose.

**Phase 0 — anchor read** is a forcing function added after a regression where prior knowledge existed in a memory index but had never been read into the actual session context. Before any planning code runs, the skill explicitly opens every reference document whose subject overlaps the sprint scope.

## Reactive loop (discovered work)

```
  diagnose [target]
       ↓
  .diagnose/findings-<timestamp>.md
       ↓
  fix-triage
       ↓
  .fixes/triage-<task-id>.{md,json}
       ↓
  sprint-execute --fix <task-id>
       ↓
  Per-unit: implement → acceptance probe → checkpoint
       ↓
  .fixes/checkpoint-<task-id>.json
       ↓
  fix-verify <task-id>
       ↓
  .fixes/verify-<task-id>.{md,json}  →  safe_to_close ? true : escalate
```

The reactive loop handles findings discovered during diagnosis (whether of code, plans, or other artifacts). Each finding becomes a tagged severity item; each fix becomes a **unit** with a concrete acceptance probe; each unit's probe must pass before the next unit starts.

## Why two loops, not one

A forward loop without a reactive loop accumulates silent debt — findings get logged but never close. A reactive loop without a forward loop produces only fire-fighting. The two share a common runtime (`sprint-execute` handles both via mode flag `--fix`) so the cognitive cost of context-switching is minimal.

## State files (shared contract)

| File | Owner | Read by |
|---|---|---|
| `spec.md` | `project-plan` | All skills |
| `constraints.md` | `project-plan` | All skills |
| `sprints/sprint_NN_*.md` | `sprint-generator` | `sprint-execute` |
| `.checkpoint.json` | `sprint-execute` | `catchup`, `sprint-execute` (resume) |
| `.diagnose/findings-*.md` | `diagnose` | `fix-triage`, `sprint-execute` (gate query) |
| `.fixes/triage-*.{md,json}` | `fix-triage` | `sprint-execute --fix` |
| `.fixes/checkpoint-*.json` | `sprint-execute --fix` | `fix-verify`, resume |
| `.fixes/verify-*.{md,json}` | `fix-verify` | `sprint-execute` (gate query) |
| `handoffs/handoff_*.md` | `sprint-execute`, `session-close` | Next session startup |

Every artifact is plain-text and human-readable. Machine-readable variants (`.json`) exist alongside Markdown variants where automation needs to consume them.

## Hooks layer (cross-cutting)

Hooks attach to lifecycle events of Claude Code itself, independent of which skill is running. They enforce invariants that should hold regardless of whether the current work is planned or reactive:

- `PreToolUse` hooks reject calls that would inject markdown headings into capture mechanisms, or invoke destructive remote operations without explicit authorization
- `PostToolUse` hooks capture incremental learnings when documentation is edited
- `SessionStart` hooks inject prior corrections relevant to the current working directory
- `Stop` hooks finalize: drain learnings, log token usage, validate handoff vocabulary
- `PreCompact` hooks preserve memory across context-window compaction

See `hooks-overview.md` for the per-hook contract.

## Memory discipline (cross-cutting rule)

Skills should not start substantive work in a topic that has an existing reference document without first reading that document in full. The contents of a memory index are **pointers**, not **content**. Treating one-line descriptions as sufficient knowledge is the most common cause of session-level regressions.

The rule is enforced by convention in the per-skill checklists (`Phase 0` in `sprint-execute`) and reinforced by hook-driven session injection (`session_start_inject.py`).
