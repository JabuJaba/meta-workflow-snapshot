# Planned — Next Evaluations and Tests

What I plan to evaluate, test, or instrument next, in rough priority order. Each item has a trigger condition or an explicit pilot scope so it doesn't sit in "someday."

This list is mined from outstanding evaluation entries (`evaluations.md` rows marked `test` or `standby`) plus the open questions in `insights.md`.

## Near-term (next 1–2 weeks)

### Stand up local observability backend (SigNoz + WSL2 + OTEL)

**Why now.** Several decisions are currently faith-based — which hooks are firing, where token budget goes, whether memory injection is helping or just adding noise. SigNoz pilot is the prerequisite for ~3 downstream evaluations.

**Scope.** WSL2 Ubuntu + Docker Compose + SigNoz; instrument the existing hook layer (helper already pre-instrumented, currently no-op until `HOOK_OTEL_ENABLE=1`); run 1 week collecting baseline.

**What I'll learn.**
- Hook fire frequency — which hooks are paying their cost in tokens, which aren't
- Memory inject byte distribution — handoff vs. learnings_db vs. other sources
- Session length distribution — short sessions ignoring memory vs. long sessions exhausting it

**Decision after.** Cut hooks that fire never; tune inject volume; re-open the claude-mem re-evaluation with measurement instead of faith.

### Re-evaluate claude-mem with instrumented data

**Why now.** The 2026-05-16 teardown was conservative (chroma-mcp was degraded; native auto-memory was running; duplication was clear). But the rejection was provisional. After observability lands, I can re-run with real measurement.

**Scope.** Re-enable claude-mem in one project for 2 weeks; measure: SessionStart inject latency, recall precision against a 10-question holdout, cost delta per session (haiku calls for embedding work add up).

**Decision after.** Final ADR (this would be the project's 24th architectural decision record) — keep, discard permanently, or document the comparison as inconclusive.

### Hermes Agent — self-evolving skills pilot

**Why now.** Compounding skill creation is the only category my setup doesn't address. Even if Hermes' quality is lower than hand-authored, coverage is the question.

**Scope.** Hermes running in parallel on one isolated project (probably a small scraping project where skill scope is well-bounded), 2 weeks. Compare: skills auto-created by Hermes vs. skills I would have written manually.

**Decision after.** Adopt as a separate-process companion to Claude Code, or discard with a clear reason.

## Mid-term (next 1–2 months)

### Forcing functions for "signal" (complementing the existing ones for "noise")

**Two specific hooks to build:**

1. **Gotcha-capture gate.** A `Stop` hook that blocks session close if newly-observed gotcha-shaped content in the transcript has no corresponding edit in any `CLAUDE.md` from the session. Today, capture depends on me remembering to log; this would invert it.
2. **Estimate-vs-real reconcile.** Sprint handoffs would require a one-line reconciliation (`Real: Xh / Estimated: Yh / Drift: Zh`) before `Stop` approves. Drift becomes visible per sprint rather than accumulating silently.

**Why ordered after observability.** Without measurement, I can't tell whether these gates are firing on the right signal or producing more false positives than they prevent.

### Vector store foundation (RAG Level 4)

**Scope.** Qdrant local instance + `sentence-transformers/all-MiniLM-L6-v2` embedder + a unified schema across `learnings.db`, handoff bodies, ADR bodies, and reference documents. Backfill from existing artifacts (small; this is single-user data). Enable Level 4 of the gate-query hierarchy in `sprint-execute` Step 1.5.

**Decision threshold.** Don't tune score thresholds before the store is populated and used for two weeks. The empirical score distribution will dictate thresholds; choosing them ex ante is premature optimization.

### Hybrid scoring (Park 2023 + dynamic queries)

**Depends on.** Vector store running first.

**Scope.** Add BM25 alongside embedding score; blend per Park 2023 (or whatever the empirical best blend ratio turns out to be on the local data); dynamic query generation per turn for `UserPromptSubmit` semantic recall.

**Question to answer.** Does this materially beat tightened grep on the kinds of queries that actually fire? My prior is that grep is good enough for 80% of cases; this experiment is to find out where the marginal 20% lives.

### Intra-session semantic recall

**Depends on.** Hybrid scoring running.

**Scope.** A `UserPromptSubmit` hook that issues a quick semantic query per user turn and injects matched items into context, gated by a score threshold tuned from the prior step.

**Risk.** Adding context per turn raises token budget. The win has to be measurable to justify the cost.

### Rule-to-hook DSL

**Scope.** A small declarative language for rules that compile to runnable hooks. Today, registering a new gotcha as an enforced rule requires writing a Python hook by hand. A line like `never edit X without first reading Y` should be expressible as one DSL declaration that emits a `PreToolUse` matcher.

**Why later.** Useful only after enough rules exist to make per-rule hook authoring painful. Premature if the rule set is still small.

## Longer-term / conditional

### CLAUDE.md hygiene tooling

**Trigger.** When two or more active projects have `CLAUDE.md` files that have visibly drifted (duplicate sections, conflicting rules, formatting variance).

**Scope.** Dedup + linter pair (one of which — `cclint` — is already in the `test` queue). Auto-flushed sections protected from accidental clobbering.

### External tool adoption decisions (post-observability)

**Trigger.** Observability backend live and ≥1 week of data.

**Scope.** A structured re-comparison of the major memory-and-recall plugins (claude-mem, mem0, simplemem, openwolf, hermes-agent) against the instrumented baseline. Each gets one ADR. The current `evaluations.md` rows for these are best-faith decisions made without instrumentation; this round replaces them with data-backed ones.

### Transition to a narrower agent surface

**Trigger.** Workflow surface stabilizes — when the loop's components stop changing meaningfully session-to-session.

**Scope.** A handoff artifact that captures the verified, stable parts of the workflow (skills, hooks, conventions) and lists discarded experiments. The artifact would seed a downstream agent's prompt, narrowing the experimental surface to the working subset.

**Why this matters at the team level.** A workflow that only one person can run is fragile. A workflow with a clean handoff surface — "here are the 10 skills, 5 hooks, and 7 conventions that have all been verified individually" — can be picked up by another engineer or another agent without inheriting the experimental scar tissue.

## Out of scope (deliberately not on the list)

- **Migrating to LangChain / LangGraph.** Verdict already reached (see `evaluations.md`); not coming back without a category change.
- **Re-evaluating Langfuse for Claude Code.** Maintainer-confirmed structural mismatch; track discussion #9242 for category change, no work allocated.
- **Frontend / web-quality skills.** No project in scope has a web component.
- **Multi-agent orchestration platforms** (Multica, Archon, a2a-protocol). All `standby` until parallel agent count rises.

---

## How to read this

Items higher on the list are committed; items lower have explicit trigger conditions. Nothing here is aspirational — every line either has a scope and a decision condition, or it has a trigger that fires unambiguously.
