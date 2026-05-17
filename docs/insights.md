# Insights — Distilled Lessons

## The three that matter most

- **The model is rarely the bottleneck — non-deterministic recall is.** Documented knowledge that exists as an index entry but isn't read into session context produces the same regressions, repeatedly. Fix: explicit "anchor-read" before any planning step; treat indexes as pointers, never as content.
- **Forcing functions beat reactive search.** A hook that fails loudly when a known-bad pattern reappears is worth more than a semantic search that *might* surface the past lesson when queried. Determinism beats probability for invariants you can articulate.
- **Acceptance probes are the gate.** A finding with a concrete, executable probe closes in one to two iterations. A finding without one gets parked indefinitely. The cheapest discipline with the highest return.

The seven lessons below are ordered by how much each changed my actual practice. The first three reshaped the workflow; the rest are reinforcing.

---

Conclusions I've reached from running this workflow on real projects over several months. Each insight is a claim, the evidence it rests on, and the consequence for how I build today. Where evidence is qualitative or limited to my own usage, I say so.

---

## 1. The model is rarely the bottleneck. Recall is.

**Claim.** With Claude Code on Opus / Sonnet 4.x, capability ceilings are not what's costing time on real work. What costs time is the model re-litigating decisions that were already made, or re-discovering gotchas that were already documented.

**Evidence.** When I started instrumenting where sessions repeated themselves, the same pattern kept showing up: a memory index existed (one-line descriptions in a top-level `MEMORY.md`); the relevant reference document existed (full content in `reference_*.md`); the model had loaded the index at session start but had never loaded the content. So it would start a new line of investigation that the reference document would have closed in two minutes. One concrete instance cost six hours of investigation before the recipient (me) realized the answer was already written down.

**Consequence.** I introduced a "Phase 0 — anchor read" step in `sprint-execute`: before any implementation, the skill enumerates reference documents whose subject overlaps the sprint scope and reads them in full. The index is treated as a pointer, never as content. This is the single highest-leverage change I've made; the regression class it eliminates was previously the #1 source of wasted hours.

---

## 2. Forcing functions beat reactive search.

**Claim.** A hook that fails loudly when a known-bad pattern reappears is worth more than a semantic search that *might* surface the past lesson when queried. Determinism beats probability for invariants.

**Evidence.** Two cases shaped this view.

First: handoffs were using `deployed`, `ready`, `done` to describe artifacts — but those terms conflate "the file exists" with "the system was observed working end-to-end." I started writing handoffs that overstated progress without noticing. The fix that worked was a `Stop` hook (`handoff_vocab_check.py`) that fails session close if a recently-edited handoff/ADR uses ambiguous vocabulary. It's annoying when violated — which is the point. The cost of writing `built / installed / verified` correctly is trivially low; the cost of catching the slip later, when a downstream consumer reads the handoff, is high.

Second: the `learnings.db` capture mechanism was over-capturing user "corrections" because the patterns matched common Portuguese substrings (`para`, `sempre`, `stop`). Once tightened to context-anchored patterns (negation + specific object, counted re-statements, named gotchas), false-positive rate dropped by roughly an order of magnitude and the inject-at-session-start became signal instead of noise.

**Consequence.** I prefer to invest a hook over a search. When I notice a class of regression repeating, the question I ask is "what would make this fail loudly the next time?" — not "how do I make the model better at remembering?"

---

## 3. Acceptance probes are the highest-leverage discipline in the reactive loop.

**Claim.** A finding with a concrete, executable acceptance probe at triage time closes in one to two iterations. A finding without a probe gets parked in `Deferred` indefinitely. The probe is the gate; everything else is plumbing.

**Evidence.** I ran the diagnose → triage → execute → verify loop on multiple sprint targets. Findings with probes (`pytest tests/test_descricao_especie.py -v` → expect `12/12 passing`) consistently moved to closed. Findings without probes ("verify manually that the field is right") got bounced between sessions, often gained additional unrelated changes during attempts to fix them, and frequently were "fixed" without actually being closed — only re-surfaced by a later diagnose.

**Consequence.** `/fix-triage` refuses to generate a fix-unit without a concrete `probe` and `expected`. If neither can be written, the finding goes to a `needs-clarification` section. This refusal is a contract — it's enforced in the skill, not advisory.

---

## 4. Evaluating an external tool without comparing it to the incumbent is faith, not engineering.

**Claim.** "We already have X, so Y is redundant" is the most common bad call in tool evaluation. The discipline is to either measure both, or downgrade the rejection to "stand-by until measured."

**Evidence.** I caught myself doing this with at least three memory-system candidates (claude-mem, mem0, simplemem). In each case, the initial verdict was "we already have native auto-memory + custom hooks, so redundant." After Tier 3 verification revealed that claude-mem was running with degraded semantic search (chroma-mcp errors in logs) and that native auto-memory had not in fact covered the cases that motivated the evaluation, the verdict became more nuanced: `discard` pending re-measurement once observability is in place. The earlier "redundant" framing was effectively a refusal to measure.

**Consequence.** The verdict vocabulary in `evaluations.md` separates "structural mismatch" (`discard`) from "valid value, wrong timing" (`standby`). Every `discard` in that document has a one-line reason that survives a Tier 3 challenge. When the reason is "already have X," I downgrade to `standby` and write the comparison plan.

---

## 5. Vocabulary discipline is the cheapest way to keep handoffs honest.

**Claim.** Distinguishing `built` from `verified`, `installed` from `running`, `compiled` from `tested` is a thirty-second writing change with a massive downstream payoff. The same words across teams must mean the same things or every handoff becomes a translation exercise.

**Evidence.** Before the discipline, "this is done" meant whatever the writer felt. After: every handoff has explicit state per artifact. When a future session resumes, it reads `built but not verified` and knows that running the test suite is the first action, not a sanity-check. Estimated time spent on "what did I actually leave running last time?" dropped to near zero.

**Consequence.** The `handoff_vocab_check.py` hook is mandatory. Sprint handoffs follow a fixed template. ADRs use the same vocabulary. The cost of standardizing on six terms (built / installed / compiled / running / verified / tested) is small enough that there's no reason not to.

---

## 6. The reactive loop must close — not just discover.

**Claim.** Many teams run a "diagnose / audit" step that produces findings, and then the findings sit in a markdown file. The bottleneck isn't the diagnose. It's the absence of a structured path from finding → triaged unit → executed fix → verified close.

**Evidence.** Before adding `/fix-triage` and `/fix-verify` to the loop, diagnose runs produced findings that decayed: the most severe ones got addressed ad-hoc and lost their acceptance criteria; the rest were forgotten. Adding the explicit triage step (with probes and routing) and the explicit verify step (re-run probes in clean state + `git diff` against pre-fix ref) closed the loop. The follow-up `safe_to_close: true | false` decision in `verify-*.json` became the actual close gate.

**Consequence.** I don't consider a `/diagnose` complete until the loop runs through to `safe_to_close`. Findings that don't make it through within a reasonable window are explicitly marked as known issues, not silently dropped.

---

## 7. Distinguish what's `built` from what's `verified` — including when reporting to others.

**Claim.** When summarizing a project's state to a stakeholder, the temptation is to roll everything up as "done." Resist. Even at executive level, distinguishing "we have it" from "we've seen it work" is more useful than a single status word.

**Evidence.** Personal: I've sent earlier versions of this snapshot summary that used "done" for things that were actually `built but not verified`. The recipient would reasonably assume readiness that didn't exist, and I'd then have to walk it back. The bug was upstream of the recipient — it was in my own writing discipline.

**Consequence.** This snapshot itself follows the convention: anything `built` is artifact-present; anything `verified` has had a probe pass; anything `running` is a live process. In a sprint handoff, all three appear separately if relevant.

---

## Open questions on my evaluation queue

These are the next decisions I plan to put through the same lens — included so the boundary of what I claim is explicit:

- **Whether vector-store-backed semantic recall (RAG) materially outperforms tightened grep + structured anchor-read on the kinds of queries that actually fire mid-session.** I have a Qdrant-backed plan but no empirical comparison yet. The hypothesis is that grep is sufficient for 80%+ of intra-session recall and that semantic adds value at the margins; the experiment to confirm this is in the planned column.
- **Whether the cost of standing up observability (SigNoz + WSL2 + OTEL instrumentation) pays back inside a single-user workflow.** It clearly pays back at team scale. At solo scale, I'm not sure. I plan to find out.
- **Whether self-evolving skills (Hermes-style auto-skill creation) outperform hand-authored skills.** My prior is that hand-authored wins on quality, auto-creation wins on coverage — but I haven't measured.
- **Whether the patterns I've extracted (anchor-read, probe-as-gate, vocabulary discipline) generalize beyond Claude Code.** They feel general — they're about epistemics, not about a specific CLI — but I've only run them in one stack.

Each is queued for the `test` verdict, not the `decide` verdict — pilot scope and trigger conditions are in [`planned.md`](planned.md).
