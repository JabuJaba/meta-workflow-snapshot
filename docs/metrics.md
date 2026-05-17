# Metrics — Substantiated Outcomes

A small set of measured outcomes from the workflow disciplines described in this package. Each row has a stated method, a stated source, and a level of confidence the reader can interrogate.

These are observations from a single-user, multi-month run. They are not benchmarks; they are evidence that the disciplines have measurable effect in at least one environment.

## Capture-noise reduction (highest-confidence number)

**Claim.** Tightening the regex patterns in `extract_session_corrections.py` reduced the captured-corrections database by **approximately 77% in one operation**, with all sampled removals being false positives.

**Method.** Before the change, the database held 477 captured entries. The tightening replaced broad substring matchers (`para`, `sempre`, `stop`, `chega`, `toda hora`) with context-anchored patterns (negation paired with specific objects; counted re-statements; named gotchas). After running the new regex against the existing database and removing non-matches, the count dropped to 107. A manual review of a 25-row sample from the removed set found 0 legitimate corrections — all were collisions with normal conversation. A forward-validation pass on 30 synthetic test cases (legitimate / noisy / borderline) matched expected classifications on 7/7 legitimate and rejected 29/30 noisy ones.

**Source.** Pre/post counts captured in the local database; the regex change is a single commit; the forward-validation cases are in the test set for the hook.

**Why this is the highest-confidence number in the package.** It is a one-shot, observable, reproducible delta with clear before/after counts. Most other claims in this package are about workflow shape, where measurement is harder.

## SessionStart injection volume

**Claim.** Reducing `MAX_CORRECTIONS` injected at session start from 5 to 3, plus softening the template to defer judgment to the model, **cut the injected-reminder size by roughly 40–50%** without observable loss of relevant recall.

**Method.** Two changes in `session_start_inject.py`: the per-session cap (5 → 3) and the template wording (from imperative to advisory). Observation over subsequent sessions: the model no longer treats early-session reminders as low-signal noise.

**Source.** Hook source before/after; subjective observation across sessions. **Confidence:** lower than the previous metric — this is qualitative observation, not a controlled comparison.

## Loop closure rate (qualitative)

**Claim.** Findings entering the reactive loop with a concrete acceptance probe at triage time **close in one or two iterations**. Findings without a probe **rarely close** — they get parked or get "fixed" without verification and re-surface in a later diagnose.

**Method.** Tracked across multiple `/fix-triage` runs. Findings with probes consistently moved to `verified` status. Findings parked in `Deferred` for absence of probe have not, in observed runs, made it back to active triage without explicit re-prompting.

**Source.** `.fixes/triage-*.json` and `.fixes/verify-*.json` artifacts across runs. **Confidence:** qualitative trend, not a numerical rate. The discipline-level claim is strong; a precise close-rate number would require longer instrumented runs.

## What I have not measured

The honest list:

- **Token-budget reduction from RTK / CodeGraph.** The vendor numbers (60–90% for RTK; 92% for CodeGraph) are claimed; my own measurement is pending the observability sprint. I treat the independent benchmark (25–29% on CodeGraph from a third party) as the working number until I have my own.
- **Inject precision@k** for the planned vector-store-backed recall. Placeholder until Qdrant is live.
- **AskUserQuestion rate** (proxy for agent autonomy). Captured but with a known instrumentation caveat — current transcripts don't always serialize the call as a structured item, so the measured rate undercounts.
- **Real vs. estimated hours per sprint.** No structured reconciliation yet; planned forcing function captures this once added.

These gaps are intentional: I would rather report three things I can substantiate than ten I can hand-wave.
