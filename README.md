![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)

# MCP Bridge

A shared clipboard for your Claude conversations.

Claude Code, Claude.ai, and Claude Desktop don't talk to each other. If you build something in Claude Code and want to continue in Claude.ai, you copy-paste. MCP Bridge fixes that with a tiny PostgreSQL-backed clipboard exposed over the Model Context Protocol (MCP). Save in one Claude, pick it up in another.

Optionally, the bridge also exposes a Grok-powered prompt clarity checker — but Grok is **fully optional** and the bridge works without an xAI account.

---

## A day with the bridge

Here's the loop I actually run. Every screenshot below is from the same session that produced this README — two messages (id **150** and id **156**) bouncing between four different AI clients, all reading and writing the same Postgres row.

### 1. Claude Code does the work and saves message 150

I sit in PyCharm with Claude Code. It edits files, runs commands, and when I say **"save"** it writes a session summary to the bridge. No copy-paste, no pasting diffs into another window.

![Claude Code saves a session summary to the bridge](mcp-bridge/images/calude_code_save%20message.png)

That `Saved to bridge (id 150)` line is the entire handoff. The summary now lives in Postgres on Railway, addressable by id from any other client.

### 2. ChatGPT pulls 150, reviews it, and saves the review back as 156

I switch to ChatGPT, tell it to pull the latest bridge message and review the design. It reads 150 cold — no shared chat history, no project context — and gives me a real opinion grounded in what I actually shipped.

![ChatGPT reads message 150 and reviews the design](mcp-bridge/images/chat_gpt_review.png)

Then I tell it: **don't just show me — save the corrections back to the bridge.** It writes a new message and reports the id.

![ChatGPT saves its review back to the bridge as message 156](mcp-bridge/images/chat_gpt_adding_comment_and_save.png)

Now there's a second AI's review sitting in the same table as my original summary. It's id 156, and it's no longer trapped inside any single chat session.

### 3. Back to Claude Code — pull 156 and react

I jump back to Claude Code and ask it to pull message 156. It reads ChatGPT's review and tells me which points it agrees with, which one is an actual bug I introduced, and what to fix next.

![Claude Code reads ChatGPT's feedback from the bridge](mcp-bridge/images/claude_code_reading_file.png)

### 4. Codex pulls 156 too

The bridge isn't Claude-only. Codex in PyCharm reads the same row and gives its own take. Any MCP-aware client works — the bridge is just a Postgres table behind an MCP server.

![Codex reads ChatGPT's feedback via the bridge](mcp-bridge/images/codex_reading_gpt%20feeback.png)

### 5. Claude.ai pulls 156 from the browser

Final stop on the review tour: Claude.ai in a browser reads message 156 and chimes in with its own analysis. Same row, fourth client.

![Claude.ai reads message 156 and gives its analysis](mcp-bridge/images/calude_ui%20thoughts.png)

### 6. Underneath it all — one Postgres table on Railway

If I want to peek under the hood, the Railway dashboard shows the raw `mcp_clipboard` rows. There's 150 (the Claude Code summary) and 156 (ChatGPT's review), sitting in the same table, queryable, mine.

![Railway Postgres showing rows 150 and 156](mcp-bridge/images/railway_message.png)

**That's the whole loop.** Claude Code writes 150 → ChatGPT reads it and writes 156 → Claude Code, Codex, and Claude.ai all pull 156 → Railway is the source of truth. No copy-paste. No re-explaining context. Just `save` and `receive`.

---

## What you get

| Tool | What it does | Requires Grok? |
|------|-------------|----------------|
| `clipboard_send` | Write a message to the shared clipboard | No |
| `clipboard_receive` | Read recent messages | No |
| `clipboard_clear` | Delete old messages, keep the most recent N | No |
| `ping` | Health check | No |
| `prompt_check` | Have Grok rate a prompt as `fuzzy` / `partial` / `very_clear` | **Yes** |

If you don't set `GROK_API_KEY`, `prompt_check` simply isn't registered. The other tools work unchanged.

---

## Architecture

```
Claude.ai                   Claude Code                Claude Desktop
    │                            │                          │
    ├── clipboard_send ──►  PostgreSQL  ◄── clipboard_send ─┤
    │                        (Railway)                      │
    ├── clipboard_receive ◄─────┘─────► clipboard_receive ──┤
    │                                                       │
    └── prompt_check ──► Grok (optional) ◄──────────────────┘
```

---

# Setup: deploying to Railway (step by step)

This is the easiest path. Railway gives you a Postgres database and a Python host, and your bridge gets a public HTTPS URL that any Claude client can connect to.

**Total time: ~10 minutes.**

### Prerequisites

- A free Railway account: https://railway.app
- A GitHub account (so you can fork or push this repo)
- (Optional) An xAI API key from https://console.x.ai if you want the `prompt_check` tool

### Step 1 — Fork or clone this repo

```bash
git clone https://github.com/your-username/mcp-tools.git
cd mcp-tools
```

Or click "Fork" on GitHub so you can deploy directly from your own copy.

### Step 2 — Create a new Railway project

1. Log into https://railway.app
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Authorize Railway to access your GitHub if you haven't already
4. Pick the `mcp-tools` repo you just forked
5. Railway will detect the `Dockerfile` in `mcp-bridge/` and start building

**Important:** This repo's app code lives in the `mcp-bridge/` subfolder. After Railway creates the service:

- Open the service → **Settings** → **Source**
- Set **Root Directory** to `mcp-bridge`
- Click **Redeploy** (top-right) to rebuild from the right folder

### Step 3 — Add a Postgres database

In the same Railway project:

1. Click **"+ New"** → **"Database"** → **"Add PostgreSQL"**
2. Railway provisions Postgres and creates a `DATABASE_URL` env var **on the Postgres service itself**
3. You need to share it with your bridge service:
   - Open your **bridge service** → **Variables**
   - Click **"+ New Variable"** → **"Reference Variable"**
   - Pick `DATABASE_URL` from the Postgres service

That's it for the database. The bridge auto-creates the `mcp_clipboard` table on first connection (see `mcp-bridge/utils/db.py`).

### Step 4 — Set environment variables on the bridge service

On the **bridge service** → **Variables**, add:

| Variable | Required? | Value |
|----------|----------|-------|
| `DATABASE_URL` | **Required** | Referenced from the Postgres service (Step 3) |
| `PORT` | Auto-set by Railway | (Don't set manually — Railway injects this) |
| `GROK_API_KEY` | **Optional** | Your xAI API key, only if you want `prompt_check` |

**Skipping Grok?** Just don't add `GROK_API_KEY`. The bridge will log `grok_check_skipped` at startup and only register the clipboard tools. No code changes needed.

### Step 5 — Generate the public URL

1. Bridge service → **Settings** → **Networking**
2. Click **"Generate Domain"**
3. Railway gives you a URL like `https://mcp-bridge-production-xxxx.up.railway.app`
4. Verify it works: open `https://<your-url>/health` in a browser — you should see `{"status":"ok"}`

Your MCP endpoint is `https://<your-url>/mcp/` (note the trailing slash).

---

# Connecting your Claude clients

Use the URL from Step 5 above.

### Claude Code

Create `.mcp.json` in any project root:

```json
{
  "mcpServers": {
    "mcp-bridge": {
      "type": "http",
      "url": "https://<your-railway-url>/mcp/"
    }
  }
}
```

Restart Claude Code and it'll pick up the tools. Test with: *"Use the ping tool"*.

### Claude Desktop

Edit `claude_desktop_config.json` (Settings → Developer → Edit Config):

```json
{
  "mcpServers": {
    "mcp-bridge": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://<your-railway-url>/mcp/"]
    }
  }
}
```

Restart Claude Desktop.

### Claude.ai (web)

Settings → **Connectors** → **Add custom connector** → paste your Railway MCP URL.

---

# Running locally (optional, for development)

If you'd rather run the bridge on your own machine instead of Railway:

```bash
cd mcp-bridge

# 1. Copy env template and fill in
cp .env.example .env
#   DATABASE_URL=postgresql://user:pass@localhost:5432/mcp
#   GROK_API_KEY=    ← leave blank to skip Grok
#   PORT=8000

# 2. Install
pip install -r requirements.txt

# 3. Run
python server.py
```

You'll need a local Postgres or a remote one (e.g. the Railway DB).

---

# Disabling Grok at the build level

The `prompt_check` tool is opt-in. Three ways to keep it out of your deployment:

1. **Easiest — just don't set `GROK_API_KEY`.** `tools/grok_check.py` checks for the env var at registration time and silently skips if it's missing. No other changes required.
2. **Remove the file entirely** — delete `mcp-bridge/tools/grok_check.py`. Tool auto-discovery (`tools/__init__.py`) won't find it.
3. **Trim dependencies** — if you also want a smaller image, drop these from `mcp-bridge/requirements.txt`:
   - `langgraph`
   - `langchain-xai`
   - `langchain-core`

   (Keep `pydantic` — it's used elsewhere.) Then delete `grok_check.py` and redeploy.

---

# CLAUDE.md (behavior rules)

`CLAUDE.md` in the repo root tells Claude Code *when* to use the bridge. By default, Claude only writes to the clipboard when you say keywords like **"save", "send", "bridge", "wrap up"**, and only validates with Grok when you say **"check", "validate", "grok"**. Edit `CLAUDE.md` to change these rules — it's just markdown.

---

# Project layout

```
mcp-bridge/
├── server.py              # FastMCP entry point, stateless HTTP
├── tools/
│   ├── __init__.py        # pkgutil auto-discovery of register() funcs
│   ├── clipboard.py       # clipboard_send / receive / clear
│   ├── grok_check.py      # prompt_check (skipped if no GROK_API_KEY)
│   └── health.py          # ping
├── utils/
│   ├── db.py              # asyncpg pool, auto-creates table
│   └── config_loader.py   # config.yaml + .env → Config dataclass
├── config.yaml            # Server name, version, Grok model
├── requirements.txt
├── Dockerfile             # python:3.12-slim, non-root user
└── railway.toml           # Healthcheck path = /health
.mcp.json                  # Claude Code MCP connection
CLAUDE.md                  # Claude Code behavior rules
```

---

# Adding your own tools

Drop a file in `mcp-bridge/tools/` with a `register(mcp)` function:

```python
def register(mcp):
    @mcp.tool()
    async def my_tool(arg: str) -> dict:
        """Tool description shown to Claude."""
        return {"result": "done"}
```

Auto-discovery picks it up — no extra wiring. Follow the `grok_check.py` pattern if your tool depends on an optional API key.

---

# Troubleshooting

| Problem | Fix |
|---------|-----|
| Railway build fails | Make sure **Root Directory** is set to `mcp-bridge` (Step 2). |
| `Database unreachable` in tool responses | `DATABASE_URL` not referenced from the Postgres service. Redo Step 3. |
| `prompt_check` tool missing | Expected if `GROK_API_KEY` isn't set. Add it in Railway → Variables and redeploy. |
| Claude Code doesn't see the tools | Check `.mcp.json` URL ends with `/mcp/` (trailing slash). Restart Claude Code. |
| `/health` returns 404 | The service is up but not the bridge — check Railway logs for `server_ready`. |

---

# Security warning

This is a prototype. The bridge **has no authentication**. Anyone with your Railway URL can read and write the clipboard.

Don't post your URL publicly. For shared / multi-user setups, add an auth layer first — API keys via header, OAuth, or Railway's private networking with a gateway.

Other known gaps:
- No rate limiting
- No multi-user isolation (one global clipboard)
- No test suite
- Minimal input validation

---

# Tech stack

- [**FastMCP**](https://github.com/jlowin/fastmcp) — MCP protocol server
- **asyncpg** — async Postgres driver
- **LangGraph + langchain-xai** — optional Grok integration with structured output
- **structlog** — JSON logs
- **Starlette + Uvicorn** — ASGI server
- **Railway** — host + managed Postgres

---

# Future ideas

- API key auth and per-user clipboard namespaces
- TTL / expiry on clipboard messages
- WebSocket real-time sync
- Token usage tracking per source
- Grok effectiveness metrics (`fuzzy` / `partial` / `very_clear` over time)
- Richer prompt refinement analytics

PRs and issues welcome. If you ship something on top of this, share it — that's why it's public.
