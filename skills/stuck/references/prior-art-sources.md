# Prior-art sources for /stuck — curated issue trackers by domain

Each entry: domain + canonical URLs to search BEFORE generic Google/StackOverflow.
Update incrementally when a new high-signal source is found in a real `/stuck` invocation.

## openpyxl / xlsx generation in Python

**Canonical bug tracker** (NOT GitHub mirror — actual issues live here):
- https://foss.heptapod.net/openpyxl/openpyxl/-/issues — main tracker
- Google Group: https://groups.google.com/g/openpyxl-users — long-form bug reports

**Known recurring issues** (cite directly when relevant):
- #1430 — "We found a problem with some content" on load+save with no changes
- #2019 — externalLinks corruption (fix dev'd in 3.1.5)
- #1330 — workbooks with comments cannot be saved more than once

**Cross-reference**:
- Anthropic claude-code issue #22044 — *Anthropic itself recommends refusing openpyxl on complex workbooks*. Always check this when xlsx skill is involved.
- alternative libs: xlwings (COM-based, preserves source), PyXLL (commercial), IronXL (commercial), zipfile-direct surgical edit

## Anthropic Claude Code (skills, hooks, agent issues)

**Canonical**: https://github.com/anthropics/claude-code/issues
- Search by component: `is:issue <skill_name>` or `is:issue hook <event_type>`
- Anthropic flags known internal-tool footguns here — load-bearing source

## pandas / data manipulation

- https://github.com/pandas-dev/pandas/issues — main
- Specific: ExcelWriter corruption (#33746, #44868) — different class than openpyxl direct usage
- StackOverflow tag: `[pandas]` is high-signal

## Playwright / browser automation

- https://github.com/microsoft/playwright/issues
- https://github.com/microsoft/playwright-python/issues (Python-specific)
- Anti-bot/CDP fingerprint: check `playwright-stealth` fork chain (camoufox-org, patchright, etc.)
- Cloudflare/Akamai detection: never solved by stealth alone — usually mirror site or paid API

## pyautogui / GUI automation Windows

- https://github.com/asweigart/pyautogui/issues
- Companion: pywinauto (https://github.com/pywinauto/pywinauto) — UIA backend more reliable than pyautogui for dialogs
- Common issues: dialog focus, accelerator keys, Excel/Office quirks, dark theme OCR

## ETL / data pipeline / DuckDB

- https://github.com/duckdb/duckdb/issues
- DuckDB asof_join, JSON extract performance, parquet ingestion — common stuck patterns

## LLM / agent orchestration

- LangChain: https://github.com/langchain-ai/langchain/issues
- LlamaIndex: https://github.com/run-llama/llama_index/issues
- Anthropic SDK: https://github.com/anthropics/anthropic-sdk-python/issues
- Generic patterns: prompt injection, token limits, retry-loop

## Excel-specific (when problem is Excel-side, not Python-side)

- Microsoft Q&A: https://learn.microsoft.com/en-us/answers/tags/9/office-excel
- Stellar / Repairit blog posts (commercial recovery tools — useful for diagnosing root cause via their guides)

## Search hints (anti-fluff)

- Use exact error message in quotes
- Add library name to disambiguate
- Add year (current `month/year` from claude env) for recent fixes
- Skip blog spam: prefer github.com / .readthedocs.io / google groups / official docs
- Anthropic claude-code #22044 deserves checking even when not obviously related — Anthropic flags many cross-cutting tool issues there

## When to update this file

Add a new domain entry only when:
- A `/stuck` invocation found prior-art via the source AND
- The same domain is likely to appear in 2+ projects

Don't accumulate one-off URLs. Quality over quantity.
