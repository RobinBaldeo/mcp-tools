# MCP Bridge — Claude Code Instructions

## Overview
This project has a live MCP bridge server deployed on Railway. It connects Claude Code, Claude.ai, and Claude Desktop via a shared Postgres clipboard. The server is already connected via `.mcp.json` — do NOT ask to connect or confirm connection. Just use the tools directly when instructed.

## Available Tools
- `clipboard_send(content, source, metadata)` — write a message to the bridge
- `clipboard_receive(source, limit)` — read recent messages from the bridge
- `prompt_check(prompt)` — send a prompt to Grok for blind clarity validation
- `ping()` — health check

## When to Use `clipboard_send`

### ONLY save when I explicitly say one of these keywords:
- "save", "save this", "save summary"
- "send", "send this", "send to claude"
- "bridge", "bridge this"
- "wrap up", "wrap it up"

### Do NOT save when:
- I ask general questions ("how do I do this?", "what does this mean?")
- I ask you to explain, review, or debug something
- I ask you to write or edit code (unless I also say "save")
- Normal back-and-forth conversation
- If in doubt, **don't save** — wait for me to explicitly say "save"

## When to Use `prompt_check` (Grok Validation)

### ONLY validate when I explicitly say one of these keywords:
- "check", "check this", "check the prompt"
- "validate", "validate this"
- "grok", "grok check", "run it by grok"

### Grok validation is NOT automatic — never call `prompt_check` unless I ask for it.

### Grok Check + Save Flow
When I say "check and save" or "validate and save":
1. First, generate the summary prompt (same formats as below)
2. Call `prompt_check` with the generated prompt
3. Read Grok's response:
   - **`very_clear`** → proceed to `clipboard_send` immediately
   - **`partial`** → refine the prompt based on Grok's feedback, then call `prompt_check` again. Repeat until `very_clear`, then `clipboard_send`
   - **`fuzzy`** → refine the prompt based on Grok's feedback, then call `prompt_check` again. Repeat until `very_clear`, then `clipboard_send`
4. Do NOT save anything rated `fuzzy` or `partial` — it must pass as `very_clear` first

### Standalone Grok Check
When I just say "check" or "validate" without "save":
- Run `prompt_check` and show me the result
- Do NOT save — just show the classification and feedback
- If it's `fuzzy` or `partial`, suggest improvements but wait for my instruction

## Save Formats

### Summary Mode (default)
When I say "save" or "send" without further detail, generate a summary prompt. Write it so Claude.ai can pick it up and immediately understand what was done:

```
## Session Summary — [brief title]
**Date:** [timestamp]
**Project:** [project name or path]

### What Changed
- [file1.py]: [what was done and why]
- [file2.py]: [what was done and why]

### Key Decisions
- [any architectural or design decisions made]

### Current State
- [what's working, what's not, what's next]

### Context for Pickup
[2-3 sentences briefing another Claude instance with enough detail to continue without asking "what did you do?"]
```

### Comprehensive Mode
When I say "comprehensive", "detailed", "full overview", or "in-depth":

```
## Comprehensive Project Overview — [project name]
**Date:** [timestamp]
**Root:** [project path]

### Architecture
- [system structure, key components, data flow]

### File-by-File Breakdown
- [every relevant file, what it does, key functions/classes]

### Configuration
- [env vars, config files, external services]

### Dependencies
- [key packages, versions, why they're used]

### Deployment
- [how it's deployed, where, Railway/Docker specifics]

### Known Issues / TODOs
- [anything broken, incomplete, or planned]

### How to Continue
[detailed instructions for another Claude instance to pick up cold]
```

### Code Snippet Mode
When I say "save this code" or "send this function":

```
## Code Snippet — [description]
**File:** [filepath]
**Language:** [language]

[the code block]

**Context:** [why this code matters, what it connects to]
```

### Error/Debug Mode
When I say "save this error" or "send this bug":

```
## Debug Context — [brief description]
**File:** [filepath]
**Error:** [error message]

### Stack Trace
[relevant trace]

### What Was Tried
- [attempted fixes]

### Suspected Cause
[analysis]
```

## When to Use `clipboard_clear`

### ONLY clear when I explicitly say one of these exact phrases:
- "clear the bridge", "clean the bridge", "wipe the bridge"

### Rules:
- NEVER suggest clearing the bridge — wait for me to say it
- NEVER ask "do you want to clear?" or "should I clean up?" — that counts as initiating
- ALWAYS keep at least 2 most recent messages (keep_last=2 minimum)
- ALWAYS tell me how many messages will be deleted before executing
- ALWAYS pass confirm="yes_delete" — the tool will reject without it
- If I say "yes" or "proceed" to something else, that is NOT permission to clear