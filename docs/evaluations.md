# Tool & Repo Evaluations

A log of external tools and open-source projects I evaluated for inclusion in an LLM agent workflow (Claude Code as primary CLI, plus surrounding infrastructure for memory, observability, code navigation, agent orchestration). Each row is a real decision with a date, a rationale, and a verdict.

49 projects evaluated as of 2026-05-17. Bias toward decisions, not exhaustive surveys — many candidates were rejected after a one-hour read of the README + a Tier 3 check of the docs / issues / discussions; only the ones that made a difference are detailed here.

The full per-entity notes (one Markdown file per project, with status, rationale, anchor risk, reversal procedure if applicable, and history of status changes) live in a private wiki. This document is the public-facing summary.

## Five decisions most worth your time

If you read only five rows from the 49 below, read these — they show how the methodology produces different verdicts on adjacent-looking tools.

| Decision | Verdict | Why this one matters |
|---|---|---|
| **CodeGraph** (colbymchenry/codegraph) | `adopt` | Tree-sitter SQLite index exposed as 7 MCP tools; independent benchmarks show 25–29% fewer read/grep calls (vendor claim of 92% was the original signal, but the independent number is what drove adoption). Removable in one command. Demonstrates "adopt when measured value is real and reversal is cheap." |
| **claude-mem** (thedotmack/claude-mem) | `discard` (provisional) | Plugin overlapped with Anthropic's native auto-memory and required disabling native to coexist. Tier 3 surfaced 19 Windows bugs + a 642-instance silent-failure issue. Teardown documented with full reversal procedure. Demonstrates "rejection with documented reversal so the decision can be re-opened with data later." |
| **Langfuse** | `discard` (clean) | Maintainer confirmed in discussion #9242: "Claude Code exports LOGS and not TRACES, thus it is currently not directly compatible." LiteLLM workaround also broken. Demonstrates "reach the maintainer for the verdict when public docs are ambiguous." |
| **SigNoz** | `test` | Apache-2.0, accepts logs + metrics + traces over gRPC (Claude Code's default), vendor-published Claude Code integration guide. Caveat: Linux/macOS only — requires WSL2 on Windows. Demonstrates "promising fit blocked by a concrete environmental constraint; pilot scheduled rather than pretended-easy." |
| **Hermes Agent** (NousResearch) | `test` | Self-evolving skills (DSPy + GEPA, ICLR 2026). Adds a capability my current setup lacks: compounding skill creation. Pilot: run in parallel on one isolated project for 2 weeks. Demonstrates "queue empirical pilots when a tool fills a genuine capability gap rather than dismiss as redundant." |

Two of these are adoptions, two are discards, one is a scheduled test. Together they show the methodology produces unambiguous outcomes when applied — not "interesting" for its own sake.

## Methodology

Each evaluation goes through up to four tiers, stopping at whichever produces a clear verdict:

1. **Tier 1** — README + repo signals (stars, recent commits, license, maintainer)
2. **Tier 2** — installation attempt or smoke test in an isolated environment
3. **Tier 3** — verification of specific claims against issues, discussions, maintainer statements, and independent benchmarks
4. **Tier 4** — empirical comparison against the incumbent in a side-by-side run (rare; reserved for high-stakes decisions like memory backends)

Verdict vocabulary is explicit:

| Status | Meaning |
|---|---|
| `adopt` | In active use |
| `adopt-conditional` | In use behind a constraint (e.g., specific OS, specific project type) |
| `implement` | Decision made; integration work in progress |
| `done` | One-shot evaluation closed (lesson extracted, no install needed) |
| `test` | Empirically promising; pilot scheduled |
| `standby` | Valid value, wrong timing or external dependency |
| `partial` | Adopted in one domain, rejected in another |
| `defer` / `defer-bookmark` | Re-evaluate when a specific trigger condition fires |
| `discard` | Structural mismatch — not coming back without a category change |

A common anti-pattern in tool evaluation is "we already have X, so Y is redundant." Whenever I caught myself dismissing a candidate that way, I forced the question: have I actually compared X and Y? Where the answer was no, the verdict became `test`, not `discard`.

---

## Adopted — in active use

| Tool | Repo | Domain | Evaluated | One-line takeaway |
|---|---|---|---|---|
| **CodeGraph** | colbymchenry/codegraph | code-navigation, token-compression | 2026-05-09 | Tree-sitter SQLite index exposed as 7 MCP tools; saves 25–29% of read/grep calls measured independently. Index per project, removable in one command. |
| **Caveman** (`caveman-compress` only) | JuliusBrussee/caveman | token-compression | 2026-05-09 | The "grunt" response mode conflicts with corporate writing standards; the memory-file compressor is adopted in isolation (~46% size reduction on `.md` memory files). |
| **Camoufox** | daijro/camoufox | scraping / anti-bot | — | Fingerprint-spoofing Firefox fork; in use for OSINT scraping where Playwright defaults are detected. |
| **Windows MCP** | — | env adapter | — | Tooling adapter for Windows-native Claude Code; resolves PowerShell vs. Bash routing quirks. |
| **wshobson agents** | wshobson/agents | agent prompts | — | Reference set of agent prompt patterns adopted as starting points for specialized roles. |
| **Nemotron Nano Omni** | — | local LLM | — | Local model adopted for routing simple tasks off the API path. |
| **MCPControl** | — | mcp orchestration | — | Local MCP server lifecycle control. |
| **OmniParser** | microsoft/OmniParser | UI vision | — | Adopted conditionally for vision-based UI tasks; not active in general workflow. |
| **RTK** | rtk-ai/rtk | token-compression | 2026-05-09 | CLI output proxy compresses git/pytest/ruff output by 60–90% before it reaches the model. **adopt-conditional**: it recommends WSL on Windows; held back until I migrate or measure that CLI output is exceeding 20% of the token budget. |

## Implement — integration in progress

| Tool | Repo | Domain | Evaluated | Status |
|---|---|---|---|---|
| **LeanKG** | FreePeak/LeanKG | knowledge-graph, mcp | 2026-04-18 | Knowledge graph + MCP server for codebase impact analysis. Claimed 98% token reduction on impact analysis; chosen as the most differentiated option in the code-navigation category (no equivalent in the current setup). First integration: a multi-package Python project where dependency analysis is the highest cost. |
| **Moonshine v2** | — | local LLM (STT) | 2026-05-02 | Speech-to-text local model adopted for transcript-heavy workflows. |
| **claude-md-management** plugin | — | memory-system | 2026-05-10 | Plugin for `CLAUDE.md` lifecycle management (dedup, validation). Enabled in `settings.json`; tuning thresholds. |

## One-shot evaluations closed (`done`)

| Tool | Lesson extracted | Action taken |
|---|---|---|
| **karpathy-skills** | A minimalist `CLAUDE.md` with 4 behavioral rules outperforms a long ruleset on adherence | Rules 3 (surgical changes) and 4 (plan with verify) extracted into the local `feedback_behavior.md`; no plugin installed. |
| **mast-taxonomy** | Agent-failure taxonomy provides shared vocabulary for diagnosing recurring agent issues | Taxonomy adopted as reference; no integration needed beyond reading. |

## Testing — empirically promising, pilot scheduled

| Tool | Repo | Domain | Evaluated | What I'm measuring |
|---|---|---|---|---|
| **SigNoz** | SigNoz/signoz | observability | 2026-05-10 | OTLP backend that accepts Claude Code's logs + metrics + traces over gRPC. Apache-2.0, self-hosted. Caveat: Linux/macOS only — requires WSL2 on Windows. Setup guide written; pilot deferred to the observability sprint. |
| **Hermes Agent** | NousResearch/hermes-agent | memory / agent | 2026-04-18 | Self-evolving skills (DSPy + GEPA, ICLR 2026). Compounding skill creation is a capability my current setup does not have. Pilot: run in parallel on one isolated project for 2 weeks; compare auto-created skills against manually written ones. |
| **cclint** | felixgeelhaar/cclint | memory-system | 2026-05-10 | Linter for `CLAUDE.md` files; needed once `CLAUDE.md`s in multiple active projects start drifting. |
| **Qwen3 TTS** | — | local LLM | 2026-05-02 | Local TTS model under evaluation against incumbent. |

## Stand-by — value clear, timing wrong

| Tool | Repo | Why on hold | Re-evaluate when |
|---|---|---|---|
| **Archon** | coleam00/Archon | YAML workflow engine for agents; v1 archived, project still maturing. Setup overhead high for single-user. | When operating 3+ parallel agents on the same workflow shape. |
| **mem0** | mem0ai/mem0 | Memory backend with extraction layer. Held back: I want to see SigNoz data before adding another memory layer. | After observability is live and capture noise/precision can be measured. |
| **Multica** | multica-ai/multica | "Jira for agents." Infrastructure-heavy for solo use. | When parallel agent count rises. |
| **a2a-protocol** | — | Agent-to-agent protocol; premature for single-agent workflow. | When multi-agent topology exists. |
| **claude-telemetry-technickai** | technickai/* | Alternative telemetry shim; SigNoz is the chosen path. | If SigNoz pilot fails. |
| **disler hooks-mastery** | disler/* | Hook patterns repository; adopted patterns will be picked off opportunistically rather than installing the whole thing. | As specific patterns become needed. |
| **simplemem** | — | Lightweight memory candidate; in the same category as mem0 and waiting on the same data. | Post-observability. |

## Partial — adopted in one domain, rejected elsewhere

| Tool | Adopted for | Rejected for |
|---|---|---|
| **LinkedIn MCP server v1** | OSINT enrichment on candidate research | Bulk operations — rate limits and API contract drift make automation brittle. |
| **handoff-v2** schema | New handoff documents | Backfilling old handoffs — cost exceeds value for archived sprints. |

## Deferred — re-evaluate on trigger

| Tool | Trigger to re-open |
|---|---|
| **Scrapling** | When a scraping target requires its specific anti-bot features. |
| **Camofox browser** | If Camoufox stops being maintained or a target site adds detection it doesn't beat. |

## Discarded — the eight most informative

Discards are documented because they are evidence of how decisions were made, not because the projects are bad. Several are excellent in their intended context but don't fit this stack. The eight rows below carry the most signal; another twelve discards with thinner rationale are archived at the end of this document.

| Tool | Domain | Reason for discard |
|---|---|---|
| **claude-mem** | memory-system | Runs alongside Anthropic's native auto-memory (v2.1.59+) and requires `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` to avoid duplication — implies overlapping coverage. Independent verification: chroma-mcp degraded in logs (8 projects hit MCP -32000 errors), so semantic search was effectively non-functional during normal use. Tier 3 surfaced 19 documented Windows bugs and a 642-instance silent-failure issue (#2292). Teardown procedure documented and reversible — not a permanent reject; flagged for re-measurement once observability is live. |
| **Langfuse** | observability | Maintainer confirmed in discussion #9242: *"Claude Code exports LOGS and not TRACES, thus it is currently not directly compatible."* LiteLLM proxy workaround also confirmed broken. Clean structural mismatch — verdict closed cleanly. |
| **Letta** | memory-system | Memory framework focused on long-running agents; mismatched with the stateless session model of Claude Code. Useful in its intended context — a different stack would adopt it. |
| **arag** | memory-system | RAG variant without a differentiator over a vanilla embedding + BM25 hybrid. Example of a discard where the right verdict is "no marginal value" rather than "structural mismatch." |
| **LangSmith / LangGraph** | observability + orchestration | Bound to the LangChain ecosystem; adoption would require rewriting the stack into LangChain. Listed together because the rationale is the same: tool fit assumes a framework choice my stack has not made. |
| **Arize Phoenix** | observability | Elastic License 2.0 — not OSI-free; usage restrictions incompatible with my licensing policy. License-driven discards are uncommon but worth surfacing because the rationale travels even to projects that look technically excellent. |
| **Addy Osmani's `agent-skills` and `web-quality-skills`** | agent prompts | Skills targeted at web/frontend engineering (Lighthouse, Core Web Vitals, WCAG); my use cases are Python pipelines and scrapers with no UI component. Domain mismatch, not quality issue. |
| **OpenWolf** | hooks-lifecycle | Hook framework that overlaps with capabilities I've already built (`buglog.json` and re-read blocking). Re-evaluate if my custom hooks become harder to maintain than installing an opinionated framework — but until then, the overlap is the discard reason. |

## Probe-state

| Tool | Note |
|---|---|
| **proofshot** | Windows compatibility probe pending. |

---

## Discard archive (thinner rationale, kept for completeness)

Twelve additional discards with less elaborate reasoning. None of these were close calls; the rationale fits in one line.

| Tool | Domain | One-line reason |
|---|---|---|
| **mem0** (original eval; now `standby`) | memory | Initially discarded; reopened to standby pending observability data. |
| **sophia** | memory | No clear improvement over the current setup. |
| **claude-memory-compiler** | memory | Compilation step adds complexity without measured recall improvement. |
| **autoskill** | memory | Auto-generated skills lower-quality than hand-authored on observed runs. |
| **opencode-dcp** | hooks-lifecycle | Different lifecycle model than Claude Code; non-portable. |
| **zacdcook-semantic-memory** | memory | Implementation-specific; the underlying abstraction is interesting but not adoptable as code. |
| **OpenAI Agents SDK handoffs** | orchestration | OpenAI-SDK-centric; my agent path is Anthropic-centric. |
| **cloakbrowser** | scraping | Camoufox covered the same need with a clearer maintainer model. |
| **fish-speech-s2-pro** | local LLM (TTS) | TTS quality lower than alternative under test. |
| **glance** | vision | Overlap with OmniParser; OmniParser fit better. |
| **rom** | local LLM | Outside the active model size range. |

---

## What this evaluation log is not

It does not say "Tool X is better than Tool Y in general." Each verdict is conditional on **this stack** (Anthropic Claude Code as primary CLI, Windows 11 host, Python pipelines, single-agent workflow today). A different stack would produce different verdicts on most of these. The discipline I care about is making each decision explicit and recording why, not declaring universal winners.
