# Workflow — End-to-End Walkthrough

A walkthrough of a single sprint, from planning through verification. Times are illustrative; the loop is shape-stable across small and large sprints.

## 1. Planning

The user invokes `/project-plan` once per project to establish scope, success criteria, and known constraints. This produces `spec.md` and `constraints.md` — authoritative documents that every subsequent skill treats as ground truth.

Periodically (per sprint), the user invokes `/sprint-generator` with a theme. The generator reads `spec.md`, recent diagnoses, ADRs, and prior sprint outcomes, and produces `sprints/sprint_NN_<theme>.md` — a phased plan with acceptance criteria per phase.

A well-formed sprint document contains:
- **Goal**: what the sprint changes
- **Acceptance criteria**: testable conditions per phase
- **Phase 0 — Anchor Read**: list of reference documents that must be read before any implementation
- **Phases 1..N**: implementation steps with acceptance probes
- **Known risks / open decisions**

## 2. Execution

The user invokes `/sprint-execute <N>` (or with explicit path). The skill:

1. Reads the sprint doc, `spec.md`, `constraints.md`, and any prior `handoff_*.md`
2. Reads `.checkpoint.json` if present to resume
3. Loads active findings from `.diagnose/` and pending fix-units from `.fixes/` — if any of these conflict with the planned phase scope, the skill **blocks** and asks for human decision rather than silently proceeding
4. Runs Phase 0 — anchor read — explicitly opening each reference document
5. For each phase: implements, runs the phase's acceptance probe, writes `.checkpoint.json` on success

Quantitative acceptance is mandatory: `139/139 tests passing`, `704/704 rows, 0 NaN`. Exit-code zero alone is insufficient.

If interrupted, `.checkpoint.json` records `phase_in_progress`, `partial_state`, and `safe_to_resume`. The next session reads this file first; the user does not re-explain.

## 3. Closing

At sprint end, the skill writes:
- `handoffs/handoff_sprint_NN.md` — what was done, what's next, open decisions
- ADR entries for any architectural decisions made during the sprint
- CLAUDE.md updates for any new gotchas, field names, or environment rules
- `.checkpoint.json` updated to `phase_completed: N` (final)

A `Stop` hook validates the handoff's vocabulary before close — terms like `deployed`, `ready`, `done` (applied to artifacts) cause the hook to fail loudly, forcing rewording to the discipline of `built / installed / verified`.

`/session-close` is only invoked for sessions outside the sprint loop (planning, ad-hoc debug); inside a sprint, `sprint-execute` already produces the handoff.

## 4. Reactive arm — when findings appear

Findings emerge from `/diagnose`. The user invokes it on a target (a path, a subsystem, a plan, a recent fix). The skill audits adversarially across six categories — bugs, silent failures, blind spots, omissions, underestimations, negligences — and writes `.diagnose/findings-<timestamp>.md` with prioritized severity.

The user then invokes `/fix-triage`. The triage skill:
1. Ranks findings by severity × blast radius × dependency
2. Decomposes them into **fix-units** — atomic chunks with concrete acceptance probes
3. Resolves routing per unit (Claude / local model / Codex) at triage time, not execution time, so execution does not pause for routing decisions
4. Cross-references with prior triages on the same files to detect duplicates and regressions
5. Writes `.fixes/triage-<task-id>.{md,json}`

The user invokes `/sprint-execute --fix <task-id>`. The skill switches mode: instead of sprint phases, it iterates units in execution order. For each unit:
1. Run declared prerequisites (`backup`, `sanity-check`) if any
2. Implement the change — strictly scoped to the unit's findings (no opportunistic refactoring)
3. Run the acceptance probe; output must match `expected` quantitatively
4. Write `.fixes/checkpoint-<task-id>.json`

If a probe fails, the loop stops — no proceeding to the next unit until the current one passes or is explicitly escalated.

After all units pass, the user invokes `/fix-verify <task-id>`. The verification skill re-runs every probe in a clean state, computes `git diff` against the pre-fix ref to confirm only declared files were touched, and writes `.fixes/verify-<task-id>.{md,json}` with `safe_to_close: true|false`.

Only after `safe_to_close: true` is the work considered closed.

## 5. The forcing functions

Two patterns in this workflow do most of the heavy lifting:

**Acceptance probes as gates.** Every fix-unit and every sprint phase has a concrete probe. The skill refuses to advance without a quantitative match. This eliminates the "looks fine to me" failure mode.

**Vocabulary discipline.** "Built" and "verified" mean different things. A handoff that says "deployed" without supporting evidence triggers a hook failure on `Stop`. The hook is annoying when violated, which is the point — it makes the discipline cheap to maintain.

## 6. What this workflow does not give you

- It does not run unattended (each loop iteration is human-initiated)
- It does not learn semantically — recall is grep-based by default, with optional vector search as Level 4 of a fallback hierarchy
- It does not test correctness of LLM reasoning beyond what the acceptance probes catch
- It does not replace ADRs or design discussion — sprint planning still requires human judgment

These are deliberate scope boundaries, not omissions. See `roadmap.md` for capabilities under consideration.
