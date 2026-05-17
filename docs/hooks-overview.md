# Hooks — Overview

Five hook scripts are bundled in `hooks/`. They attach to lifecycle events of Claude Code and enforce invariants that should hold across all skills.

A hook becomes active only when registered in `~/.claude/settings.json` under the appropriate event key. The presence of a `.py` file on disk is not sufficient.

## At a glance

| Hook | Event | Purpose |
|---|---|---|
| `injection_guard.py` | `PreToolUse` | Reject Bash invocations that would inject markdown headings, oversized payloads, or destructive remote operations into capture paths |
| `extract_session_corrections.py` | `Stop` | Mine the just-closed transcript for user corrections, persist tightened-regex hits |
| `session_start_inject.py` | `SessionStart` | Load top-N recent corrections relevant to the current working directory and inject as a system reminder |
| `auto_learn_from_claude_md.py` | `PostToolUse` (Edit/Write) | When a `CLAUDE.md` is edited, queue the appended lines as candidate learnings |
| `handoff_vocab_check.py` | `Stop` | Reject session close if recently-touched handoff/ADR files use ambiguous terminal vocabulary (`deployed`, `done`, `ready`) for artifacts |

## Per-hook contracts

### `injection_guard.py` — PreToolUse

**Decision shape**: exit code 2 to block, exit code 0 to allow.

**What it rejects:**
- Bash calls to the local capture script (`learn.py`) where the argument contains markdown headings, exceeds 300 characters, or matches injection keyword patterns
- Invocations of destructive remote MCP operations (e.g., social-network post creation/deletion, email send/delete, database writes) without explicit authorization in the parent message

**Why it exists**: capture scripts are reachable via Bash invocations that an attacker (or an over-eager assistant) could exploit to insert misleading content into long-term learning stores. The guard makes the dangerous path noisy.

### `extract_session_corrections.py` — Stop

**Decision shape**: write-only; appends to a local capture database.

**Behavior**: scans the transcript of the just-closed session for user turns matching a tightened regex set. The patterns target unambiguous correction signals (negation paired with specific objects, counted re-statements, named gotchas) rather than substring matches on common verbs.

**Why the tightening matters**: an earlier version of the patterns matched substrings like `para`, `sempre`, `stop` — these collided with normal Portuguese conversation and accumulated a large false-positive rate. The current patterns prioritize precision over recall; a missed correction is better than a noise-laden capture.

### `session_start_inject.py` — SessionStart

**Decision shape**: emit a `<system-reminder>` block to inject prior corrections relevant to the current `cwd`.

**Behavior**: query the capture database for items tagged to the current project, ranked by recency. Inject the top items (default: 3) with a softened template that prompts the model to verify against current code before treating as authoritative.

**Why low N**: noise in injected context costs tokens and degrades attention. Three high-recency hits outperform ten stale ones.

### `auto_learn_from_claude_md.py` — PostToolUse (Edit / Write)

**Decision shape**: write-only; queues a candidate learning.

**Behavior**: when a `CLAUDE.md` is edited, capture the recent appended lines (default: 25) and stage them for the drain pass in `Stop`. This is the primary mechanism for capturing gotchas discovered mid-session — the user does not need to remember to log; editing CLAUDE.md is the trigger.

**Trade-off**: this captures everything edited, including paragraphs that the user later removed in the same session. Triage happens at drain time; this hook stays cheap.

### `handoff_vocab_check.py` — Stop

**Decision shape**: exit code 2 (block) if a violation is found in any handoff/ADR file modified during the session; exit code 0 otherwise.

**Behavior**: scan files matching `handoff_*.md`, `HANDOFF.md`, `ADR.md` for terms in the "ambiguous" set (`deployed`, `ready`, `done`, equivalents) used in contexts that look like artifact-state assertions. If a violation is found, fail the close and report the line.

**Why it matters**: this is the cheapest forcing function for distinguishing "built" from "verified". Skipping it once means weeks of handoffs that overstate progress.

## Hooks intentionally not bundled

Several hooks in the working environment are not included here because they are either tied to specific local infrastructure (token-logging backends, telemetry endpoints, MCP health gates pointing at private services), or because they are utilities invoked from the CLI rather than registered as Claude Code hooks. Adapt as needed.

## Configuration snippet (illustrative — do not copy-paste blindly)

This is an **example** of the registration shape. If you already have hooks configured in `~/.claude/settings.json`, **merge** these entries into the existing arrays rather than replacing the whole `hooks` object — overwriting would remove anything you already have. The minimum shape:

```json
{
  "hooks": {
    "PreToolUse": [{
      "hooks": [{
        "type": "command",
        "command": "python ~/.claude/hooks/injection_guard.py",
        "timeout": 10
      }]
    }],
    "PostToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{
        "type": "command",
        "command": "python ~/.claude/hooks/auto_learn_from_claude_md.py",
        "timeout": 10
      }]
    }],
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "python ~/.claude/hooks/session_start_inject.py",
        "timeout": 10
      }]
    }],
    "Stop": [{
      "hooks": [
        {"type": "command", "command": "python ~/.claude/hooks/extract_session_corrections.py", "timeout": 15},
        {"type": "command", "command": "python ~/.claude/hooks/handoff_vocab_check.py", "timeout": 10}
      ]
    }]
  }
}
```

Inspect the actual `.py` files for the exact contracts and refine the timeouts based on observed performance in your environment.
