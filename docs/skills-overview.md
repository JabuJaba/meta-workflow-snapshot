# Skills — Overview

Eleven skills are bundled in `skills/`. Each is a folder containing a `SKILL.md` (the slash-command contract) and any auxiliary files the skill reads at runtime.

To install: copy the skill folder into `~/.claude/skills/`. Claude Code discovers it automatically; no registration step.

## At a glance

### Core loop

| Skill | Loop position | Purpose |
|---|---|---|
| `project-plan` | Forward — bootstrap | Run a discovery interview, then emit `spec.md`, `constraints.md`, and an initial set of sprint files with an explicit draft-and-approval gate before writing anything |
| `sprint-generator` | Forward — planning | Read `spec.md` + recent diagnoses + ADRs, emit `sprints/sprint_NN_<theme>.md` with phased acceptance criteria |
| `sprint-execute` | Forward — execution + reactive — execution | Phase-by-phase execution with checkpointing; doubles as `--fix <task-id>` runner for unit-by-unit reactive work |
| `diagnose` | Reactive — discovery | Adversarial audit across six categories; emit `.diagnose/findings-<timestamp>.md` with severity tags |
| `fix-triage` | Reactive — planning | Rank findings, decompose into fix-units with concrete acceptance probes, resolve routing per unit, emit `.fixes/triage-<task-id>.{md,json}` |
| `fix-verify` | Reactive — closing | Re-run all probes in clean state, compute git diff against pre-fix ref, emit `.fixes/verify-<task-id>.{md,json}` with `safe_to_close` decision |

### Supporting

| Skill | Loop position | Purpose |
|---|---|---|
| `brainstorm` | Pre-planning | Explicit "no implementation" mode — generate options, weigh trade-offs, surface assumptions before committing to a plan |
| `sanity-check` | Pre-build | Reuse-first investigation: search GitHub, papers, and communities for prior art before building a non-trivial component; triple-budget gate (cost × success × error); defends against prompt injection in fetched content; emits `adopt / fork / build` verdict with evidence |
| `git-prep` | One-off bootstrap | Audit a non-git project (sensitive files, large binaries, duplicates), prepare a clean `.gitignore`, dry-run reorganize before `git init`; pairs with `project-plan` as the repository-bootstrap step |
| `data-audit` | Post-execution (data pipelines) | Validate produced datasets against schema expectations, null distributions, row counts |
| `stuck` | Debugging escape hatch | When recurring errors don't converge — structured retreat: state the failed hypothesis, list ruled-out paths, surface what's missing |

## When to invoke each

### `project-plan`

Use once at the start of a new project, or when re-planning an existing one with materially changed scope. The skill runs a discovery interview (objetivo, escopo IN/OUT, technical constraints, complexity estimate, existing context), then generates a complete plan and presents a summary for approval before writing any artifact. Only after explicit approval does it emit `spec.md`, `constraints.md`, and initial sprint files. The draft-and-approval gate is the most important part — it surfaces wrong assumptions while reversal is cheap.

### `sprint-generator`

Use when you have a theme for the next sprint but no concrete plan. Inputs: project state (`spec.md`, ADRs, prior handoffs, latest diagnoses). Output: a sprint document with Phase 0 anchor read + N implementation phases, each with an acceptance probe.

### `sprint-execute`

Two modes:
- Default mode (`sprint-execute <N>` or path): execute a sprint document phase by phase, with `.checkpoint.json` written after each phase for rate-limit resilience.
- Fix mode (`sprint-execute --fix <task-id>`): execute a triage's units in declared order, with per-unit acceptance probes as gates.

In fix mode, scope discipline is enforced — the skill refuses to make changes outside the unit's declared findings. Opportunistic refactoring observed in passing must go to a follow-up triage.

### `diagnose`

Use on a target (file, subsystem, plan, recent fix). The skill audits adversarially: bugs, silent failures, blind spots, omissions, underestimations, negligences. Default scope is the entire current project; no clarifying questions before starting.

Findings are tagged NEW or KNOWN — KNOWN comes from a registry built from prior `.diagnose/findings-*.md` files, so re-runs do not re-surface already-triaged items.

### `fix-triage`

Reads the most recent `.diagnose/findings-*.md` (or an explicit path). Computes severity × blast radius × dependency, then decomposes into atomic fix-units. Each unit must have a concrete, executable acceptance probe — if no probe can be written, the finding is parked in a `Deferred` section rather than entering execution.

Routing (`agent: claude|local|codex`) is resolved at triage time, not execution time, so `sprint-execute --fix` does not pause mid-loop to ask.

### `fix-verify`

Runs after `sprint-execute --fix` completes. Re-executes every probe in a clean state, confirms only declared files were touched via `git diff` against the pre-fix ref, and emits `safe_to_close: true` or `false`. The reactive loop is only considered closed after `safe_to_close: true`.

### `brainstorm`

Use when about to commit to an approach but unsure whether it is the right one. The skill is deliberately non-destructive: no edits, no commands with side effects. It forces explicit articulation of options, the assumption each option depends on, and what would have to be true for each option to be the right one. Output is a comparison table — not a recommendation, since recommendation belongs to the user after weighing.

### `git-prep`

Use once per repository, before `git init`. The skill audits the working tree for files that look sensitive (env files, credentials, key files), large binaries that should be `.gitignored` or moved to LFS, duplicate files, and scripts with hardcoded user paths. It produces a recommended `.gitignore`, a dry-run reorganize plan (it only moves `.py` files in its default mode — Markdown / config files are left alone to preserve absolute-path references), and an audit report. Does not run `git init`. Designed to pair with `project-plan`: after the plan is approved and `spec.md` / `constraints.md` / sprints are written, `git-prep` is the step that organizes the canonical code layout and bootstraps the repository before the first sprint starts.

### `sanity-check`

Use before building any non-trivial component (browser automation, OCR, scraping anti-bot, parsers, GUI agents, ML pipelines). The skill performs reuse-first investigation: it searches GitHub, papers, and communities for prior art, then decides between **adopt** (use as-is), **fork/inspire** (adapt design ideas), or **build** (proceed from scratch) — based on evidence, not bias.

Key disciplines built in:
- **Triple-budget gate.** Before committing to external search, compute `cost × probability of success × cost of error`; only proceed if expected value exceeds 2× the cost.
- **Action ledger over token estimates.** Hard limits are stated in countable actions (WebSearch / WebFetch / Agent calls), not in token estimates, because runtime token spend is not observable.
- **Injection defense.** External content (READMEs, issues, blog posts) is treated as quoted data, never as directives. A six-pattern tamper scan runs before any fetched content is acted on.

Do not use for bug fixes, refactors, config tweaks, or any task under a day of work — the overhead exceeds the value.

### `data-audit`

Use after a pipeline produces a dataset. The skill compares row counts at boundaries (input vs. output, pre-filter vs. post-filter), checks null distributions on critical columns, verifies schema against a declared spec if present, and flags suspicious patterns (all-zero columns, dates outside expected range, encoding artifacts). Output is a structured audit report tied to the dataset version.

### `stuck`

Use after multiple iterations on the same problem have failed to converge. The skill forces a structured retreat: state the failed hypothesis explicitly, list the paths ruled out and why, surface the most likely missing information, and propose either (a) a different angle of attack or (b) escalation. Designed to break the loop where the same wrong assumption keeps being applied.

## Skills intentionally not bundled

The working environment includes additional skills that are not included in this snapshot:

- **Session-scoped utilities** (`session-close`, `catchup`): personal-workflow conveniences that depend on local conventions; not generally portable.
- **`git-publish`**: companion to `git-prep` that runs `git init`, makes the first commit, and creates the remote via `gh repo create`. Omitted to keep the snapshot focused — once `git-prep` has produced a clean tree, the remaining bootstrap is two `git` commands the user can run directly.
- **Environment-coupled routing** (`fit-evaluator`): tightly bound to hardcoded paths in the source environment; would require significant rework to make portable.
- **Generators for specific document types** (large-scale batches, codex-specific variants): retained as private until their contracts stabilize.
- **Deprecated experiments**: kept in the source environment for archaeological reasons but actively unused.

The eleven bundled skills cover the bootstrap-through-verification arc: plan a project, sanity-check before building, prep the repository (`git-prep`), generate and execute sprints, diagnose problems, triage and execute fixes, verify closure. Brainstorm and stuck handle the two edge cases (need to deliberate, need to retreat); data-audit closes the loop on data pipelines.

## Adapting before installing

Before copying any skill into your own `~/.claude/skills/`, scan its `SKILL.md` for:
- Absolute paths referencing the source environment
- File-system layout assumptions (`venv/`, `_backups/`, encoding setup specific to a host OS)
- Tool names or external commands that may not exist locally (`gh`, `python` aliasing, shell-specific syntax)
- Wiki references (e.g., `sanity-check` reads from `~/.claude/wiki/entities/`) — if the wiki structure isn't present in your environment, the skill still works in degraded mode (skipping the local prior-art lookup) but the corresponding Phase 0 block can be removed entirely if you prefer.

Each skill is small enough to read in one sitting. Treat them as starting points to fork, not as binaries to install.
