# Claude Code Meta-Workflow — Evaluation Log & Reference Snapshot

## TL;DR (read this first — 90 seconds)

**What this is.** A parallel contribution ahead of our conversation: a curated snapshot of the LLM-agent workflow I run, the 49 external tools I evaluated to get here, and the decisions and open questions that fell out. Sent now so we can discuss specifics rather than basics when we meet.

**The single strongest takeaway.** When I started instrumenting where my sessions repeated themselves, the bottleneck wasn't model capability — it was **non-deterministic recall across sessions**. A documented gotcha that existed only as a one-line index entry, never read into actual context, cost six hours on a single regression. The fix was structural: a Phase 0 "anchor-read" step that loads relevant reference docs in full before any planning begins, plus forcing-function hooks that fail loudly when a known-bad pattern reappears. This single discipline eliminated the largest single category of wasted hours in my workflow. The same shape applies to any agent system at scale.

**What I'd like you to do with this.** Read the three lead documents below (≈10 minutes if you have it; 3 minutes for the bullet summaries at the top of each). Save the rest as reference. When we meet, I'd like to apply the same evaluation lens to the agent data you shared with me — happy to come prepared with verdicts on that material specifically.

**About my operating style** (so you don't have to infer from artifacts): I evaluate explicitly before adopting (`adopt` / `discard` / `standby` with written rationale, never "looks fine"). I distinguish `built` from `verified` in every handoff. I close loops with acceptance probes before declaring done. This package is itself an example.

---

## Lead documents

If you only have ten minutes, read in this order:

1. [`docs/insights.md`](docs/insights.md) — seven distilled lessons, ordered by how much each changed my practice (3-bullet summary at the top)
2. [`docs/evaluations.md`](docs/evaluations.md) — 49 external tools and projects evaluated, with verdict and one-line takeaway per row (the five most worth your time are called out at the top)
3. [`docs/planned.md`](docs/planned.md) — what I'm testing or instrumenting next, with explicit trigger conditions

If you want the full picture afterward, the rest of the package shows *how* those decisions are operationalized: a forward planning loop, a reactive diagnosis loop, and the hooks that enforce invariants across both.

## Context for this snapshot

I work primarily on Python pipelines (financial, agricultural, OSINT) and LLM-agent infrastructure. The patterns here are domain-agnostic but were sharpened on data-pipeline work that resembles the telemetry-and-decision shape of agro / robotics SaaS. Where techniques here apply directly to your domain, they apply. Where they don't, they at least show how I'd evaluate the alternative.

## Why this exists

I run a single-person agent workflow at the same scale that many teams of three to five would. The cost structure is interesting:

- **Capability is not the bottleneck.** The model is rarely what's limiting throughput on real work.
- **Recall is the bottleneck.** The model re-discovers things that were already documented, because the documentation existed as an index entry but had never been read into session context.
- **Forcing functions beat reactive search.** A hook that fails loudly when a known-bad pattern reappears outperforms a semantic search that *might* surface the lesson when queried.

Everything in this package follows from those three observations. The skills, the hooks, the evaluation discipline, the vocabulary rules — they exist because each one cuts a specific class of regression I was observing in my own work.

## What's in the package

| Path | What you get |
|---|---|
| **`docs/insights.md`** | The seven lessons that reshaped how I build |
| **`docs/evaluations.md`** | 49 tools evaluated; adopted / testing / standby / discarded with rationale |
| **`docs/planned.md`** | Pilots and tests queued, with trigger conditions |
| `docs/architecture.md` | The two-loop architecture (forward / reactive) and the state-file contract |
| `docs/workflow.md` | End-to-end walkthrough of a sprint, planning through verification |
| `docs/hooks-overview.md` | Per-hook contract: what each hook does, when it fires, why it exists |
| `docs/skills-overview.md` | Per-skill purpose: when to invoke each, where it sits in the loop |
| `docs/roadmap.md` | Open capabilities the workflow still lacks, in dependency order |
| `docs/metrics.md` | Proportional outcome observations (claims I can substantiate; not benchmarks) |
| `hooks/` | Five `.py` hook scripts, ready to inspect or adapt |
| `skills/` | Eleven skill folders, each with a `SKILL.md` ready to drop into `~/.claude/skills/` |
| `LICENSE` | MIT |

## Audience and intent

This package is for a reader who already understands LLM-agent infrastructure and wants to see how I think — what I evaluate, how I evaluate it, and what I do with the result. The decisions matter more than the artifacts. The artifacts are included so the decisions can be checked.

This is not:
- A tutorial — there's no "how to install Claude Code"
- A product — the bundled scripts are starting points, not packaged software
- A complete inventory — projects internal to the working environment are referenced only as needed for context

## How I evaluate tools (in one paragraph)

A four-tier methodology, stopping at whichever produces a clear verdict: Tier 1 reads the README and repo signals; Tier 2 attempts installation or runs a smoke test in isolation; Tier 3 verifies specific claims against issues, discussions, and independent benchmarks; Tier 4 runs a side-by-side empirical comparison against the incumbent. Most decisions close at Tier 1 or Tier 2; the ones that don't are explicit about the verification depth. Verdict vocabulary is fixed (`adopt`, `adopt-conditional`, `implement`, `test`, `standby`, `partial`, `defer`, `discard`) and each one has a clear meaning — see `evaluations.md` for the legend.

The discipline I care about is making each decision explicit and recording why, not declaring universal winners. The same tool can be `adopt` in one stack and `discard` in another; the rationale is what travels.

## Snapshot conventions

- **This is a snapshot, not the canonical copy.** Files were exported on 2026-05-17. The canonical versions live in `~/.claude/hooks/` and `~/.claude/skills/` on a working machine. If the live source has diverged, the live source is correct.
- **Paths in scripts use `~/.claude/...` or `os.path.expanduser`.** No absolute Windows or POSIX paths are hardcoded.
- **Language is English throughout.** Some terminology overlaps with Portuguese in the working environment; this package is consistently English.
- **Public OSS project names are kept real.** I evaluated public projects (claude-mem, Qdrant, SigNoz, LeanKG, CodeGraph, Hermes, Langfuse, etc.) — naming them honestly is required for the evaluations to be credible.

## Vocabulary discipline

Handoffs and ADRs in the working environment must not use `deployed`, `ready`, `done` to describe artifacts — these conflate "the file exists" with "the system has been observed working end-to-end." A `Stop` hook (`hooks/handoff_vocab_check.py`) enforces this on session close.

| Use for artifacts | Avoid for artifacts |
|---|---|
| `built`, `installed`, `compiled` | `deployed`, `ready`, `done` |
| `running`, `started`, `stopped` (processes only) | — |
| `verified`, `tested`, `passing` (outcomes only) | — |

A minimal handoff example following the convention:

```markdown
## Sprint N — Result
- Status: built + installed + verified (5/5 phases)
- Hooks edited: extract_session_corrections.py, session_start_inject.py
- Probes: all passing (see Acceptance section)
- Process state: not currently running; restart required for next session
```

## License

MIT — see `LICENSE`.
