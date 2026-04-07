![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)

# MCP Bridge

Claude conversations lose context when switching between Claude Code, Claude.ai, and Claude Desktop. MCP Bridge solves this by providing a shared PostgreSQL-backed clipboard accessible from all three environments via the Model Context Protocol (MCP). Save a session summary from Claude Code, pick it up in Claude.ai, refine a prompt there, and pull it back into Claude Code — no copy-pasting, no context loss.

## Architecture

```
Claude.ai                   Claude Code                Claude Desktop
    │                            │                          │
    ├── clipboard_send ──►  PostgreSQL  ◄── clipboard_send ─┤
    │                        (Railway)                      │
    ├── clipboard_receive ◄─────┘─────► clipboard_receive ──┤
    │                                                       │
    └── prompt_check ──► Grok (clarity gate) ◄──────────────┘
```

The typical flow: Claude.ai crafts a detailed prompt → `clipboard_send` saves it to Postgres → Claude Code pulls it with `clipboard_receive` → executes the task → saves a summary back. Grok acts as an optional prompt validator — run `prompt_check` before saving to ensure the prompt is clear enough for another Claude instance to execute cold.

## Tools

| Tool | Description |
|------|-------------|
| `clipboard_send(content, source, metadata)` | Write a message to the shared clipboard. `source` identifies the origin (`claude_code`, `claude_ui`, `claude_desktop`). `metadata` is an optional JSON dict for tags. |
| `clipboard_receive(source, limit)` | Read recent messages. Optionally filter by `source`. Default limit is 5. |
| `prompt_check(prompt)` | Send a prompt to Grok for blind clarity validation. Returns a rating: `fuzzy`, `partial`, or `very_clear`, plus a summary of issues. |
| `ping()` | Health check. Returns server status, uptime, version, and port. |

## Project Structure

```
mcp-bridge/
├── server.py                  # FastMCP entry point, stateless HTTP, auto-discovers tools
├── tools/
│   ├── __init__.py            # register_all() — pkgutil auto-discovery
│   ├── clipboard.py           # clipboard_send / clipboard_receive
│   ├── grok_check.py          # LangGraph + ChatXAI, StructuredResponse Pydantic model, lazy singleton
│   └── health.py              # ping()
├── utils/
│   ├── db.py                  # asyncpg pool, auto-creates mcp_clipboard table
│   └── config_loader.py       # Loads config.yaml + .env into Config dataclass
├── config.yaml                # Server name, version, feature flags
├── requirements.txt           # Pinned dependencies
├── Dockerfile                 # Python 3.12-slim, non-root user
└── railway.toml               # Railway build/deploy config
.mcp.json                      # MCP server connection for Claude Code
CLAUDE.md                      # Instructions for Claude Code behavior
```

## Setup

```bash
# Clone
git clone https://github.com/your-username/mcp-bridge.git
cd mcp-bridge

# Environment
cp .env.example .env
# Fill in:
#   DATABASE_URL=postgresql://user:pass@host:5432/dbname
#   GROK_API_KEY=your-xai-api-key
#   PORT=8000

# Install
pip install -r requirements.txt

# Run locally
python server.py
```

### Deploy to Railway

```bash
railway login
railway init
railway link
railway variables set DATABASE_URL=... GROK_API_KEY=...
railway up
railway domain   # Get your public URL
```

## Connecting to Claude

### Claude Code

`.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "mcp-bridge": {
      "type": "http",
      "url": "https://your-app.up.railway.app/mcp/"
    }
  }
}
```

### Claude Desktop

`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mcp-bridge": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://your-app.up.railway.app/mcp/"]
    }
  }
}
```

### Claude.ai

Settings → Integrations → Add the Railway MCP URL.

## CLAUDE.md

The `CLAUDE.md` file controls Claude Code's behavior with the bridge:

- **Save only when explicitly told** — keywords like "save", "send", "bridge", "wrap up"
- **Grok validation only when asked** — keywords like "check", "validate", "grok"
- **Save formats** — summary (default), comprehensive, code snippet, error/debug
- **Grok gate** — when doing "check and save", the prompt must pass as `very_clear` before saving. `fuzzy` or `partial` prompts are refined until they pass.

## Adding New Tools

Create a file in `mcp-bridge/tools/` with a `register(mcp)` function:

```python
def register(mcp):
    @mcp.tool()
    async def my_tool(arg: str) -> dict:
        """Tool description."""
        return {"result": "done"}
```

The auto-discovery in `tools/__init__.py` picks it up automatically — no registration boilerplate needed.

## Tech Stack

- **[FastMCP](https://github.com/jlowin/fastmcp)** — MCP protocol server framework
- **asyncpg** — async PostgreSQL driver
- **LangGraph + langchain-xai** — Grok integration with structured output
- **structlog** — structured JSON logging
- **PyYAML + python-dotenv** — configuration
- **Starlette + Uvicorn** — ASGI server

## License

MIT
