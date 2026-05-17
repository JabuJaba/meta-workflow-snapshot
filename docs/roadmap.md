# Roadmap — Open Capabilities

This roadmap describes capabilities the workflow is still missing, in terms of **what they would do**, not specific dates. The order below is the rough current priority — earlier capabilities unblock the value of later ones.

## Foundation in place

The current state has:
- Forward loop (plan → execute → handoff) with checkpoint-based resumption
- Reactive loop (diagnose → triage → execute --fix → verify) with per-unit acceptance probes
- Capture mechanism with tightened patterns and noise-reduced session injection
- Hook-based forcing functions (injection guard, vocabulary check, auto-learn on doc edit)
- Anchor-read discipline as a session-start invariant

## Capability 1 — Forcing functions against silent regression

**Gap**: even with anchor-read discipline, two failure modes remain:
1. Closing a session after discovering a gotcha but failing to register it — the lesson dies in the volatile transcript
2. Time-estimate drift accumulating across sprints without explicit reconciliation

**Direction**: two `Stop`-hook gates. The first blocks session close if newly observed gotcha-shaped content in the transcript has no corresponding edit in `CLAUDE.md`. The second requires every sprint handoff to include a one-line reconciliation of estimated versus actual hours.

These are forcing functions for **signal**, complementing the existing forcing functions for **noise**.

## Capability 2 — Method standardization across artifact types

**Gap**: sprint documents have a known shape, but ad-hoc artifacts (status notes, PRDs, acceptance criteria, sanity-check reports, disposition logs) vary in format across instances of the same type.

**Direction**: standardize a small set of artifact templates with fixed sections — STATUS, PRD, acceptance, sanity-rule, dispositions — so that downstream skills can extract structured fields rather than interpret prose.

## Capability 3 — External memory tool evaluation

**Gap**: the current recall is deterministic (grep) with optional semantic search as a fallback level. Several external memory tools (commercial and open source) claim to improve cross-session recall. Their actual fit for this workflow is unverified.

**Direction**: a time-boxed sanity-check evaluation of two to three candidates against a real workload, with quantitative measurement of recall precision in a holdout set.

## Capability 4 — Vector-store-backed recall (RAG foundation)

**Gap**: the fallback semantic search level depends on infrastructure that is not currently running locally. Without it, all recall is grep-based and string-literal.

**Direction**: stand up a small vector store with a curated embedding model, backfill from the existing capture database, and enable Level 4 of the gate query hierarchy. Score threshold tuning happens after the store is populated — there is no benefit to choosing thresholds before observing the score distribution.

## Capability 5 — Hybrid scoring for RAG

**Gap**: pure embedding-based retrieval is known to underperform on factual queries where exact-string match matters; pure BM25 underperforms on paraphrase. Hybrid scoring (a blend of the two with dynamic query generation) is the academic standard.

**Direction**: implement a hybrid scorer after the RAG foundation exists. Calibrate against a representative query set.

## Capability 6 — Intra-session semantic recall

**Gap**: corrections from prior sessions are injected at session start, but mid-session — when the model is about to make a decision similar to a past mistake — there is no in-context retrieval beyond what was injected at startup.

**Direction**: a `UserPromptSubmit` hook performs a quick semantic query against the capture store for each user turn and injects matched items, gated by score threshold.

## Capability 7 — Rule-to-hook compilation

**Gap**: gotchas registered in `CLAUDE.md` are advisory text. The model reads them but is not forced to apply them; enforcement requires writing a custom hook per rule, which is high friction.

**Direction**: a domain-specific language for declarative rules that compile to runnable hooks. A rule like `"never edit X without first reading Y"` becomes a `PreToolUse` matcher with one line.

## Capability 8 — Documentation hygiene tooling

**Gap**: `CLAUDE.md` files in active projects drift — duplicate sections accumulate, formatting diverges. A maintenance pass requires manual reading.

**Direction**: a dedup + linter pair that operates on `CLAUDE.md` structure, with auto-flushed sections protected from accidental clobbering.

## Capability 9 — Observability with utilization metric

**Gap**: hook firing, memory injection bytes, and skill-loading overhead are not measured. Optimization is faith-based.

**Direction**: OpenTelemetry instrumentation on the hook layer with a local backend, plus a derived utilization metric. Decisions about which hooks to keep or cut become data-backed.

## Capability 10 — External tool adoption decisions

**Gap**: several plugins coexist with native Claude Code memory mechanisms. Whether each plugin adds value, duplicates effort, or actively interferes is not measured.

**Direction**: a structured comparison with a clear ADR per tool, written after the observability foundation exists so the comparison has actual data behind it.

## Capability 11 — Transition to a narrower agent surface

**Gap**: the current workflow is a meta-workspace experimented on directly. Eventually, the stable surface should narrow to a smaller agent that exposes only the verified capabilities, with the experimentation surface kept private.

**Direction**: a handoff artifact that lists the verified, stable parts of the workflow and the discarded experiments, ready to seed a narrower agent's prompt.

---

The dependency order matters: Capabilities 1–3 unlock the rest; Capability 4 is a hard prerequisite for 5–6; Capability 9 should land before Capability 10 to avoid faith-based comparisons.
