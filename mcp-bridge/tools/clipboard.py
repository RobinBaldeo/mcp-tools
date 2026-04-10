import json
from typing import Literal

import structlog
from pydantic import BaseModel, ValidationError

logger = structlog.get_logger()


class ClipboardMessage(BaseModel):
    content: str
    source: Literal["claude_ui", "claude_code", "chatgpt", "grok", "user_note"]
    metadata: dict | None = None


def register(mcp):

    @mcp.tool()
    async def clipboard_send(content: str, source: str, metadata: dict | None = None) -> dict:
        """Insert a message into the MCP clipboard.

        Args:
            content:  The text content to store. Required.

            source:   Who is sending this message. Must be one of:
                        - "claude_ui"    → Claude.ai web/mobile chat
                        - "claude_code"  → Claude Code (PyCharm / CLI)
                        - "chatgpt"      → ChatGPT (any interface)
                        - "grok"         → Grok (xAI)
                        - "user_note"    → Human-authored note or draft (not an AI response)

                      Use "user_note" any time YOU are writing the content,
                      even if you're saving it via Claude.ai. This prevents
                      AI responses and human drafts from being confused.

            metadata: Optional JSON dict for tagging. Suggested keys:
                        - "type"    e.g. "investigation_findings", "draft_prompt", "resume_extract"
                        - "topic"   short subject label
                        - "status"  e.g. "complete", "in_progress", "shelved"
        """
        try:
            msg = ClipboardMessage(content=content, source=source, metadata=metadata)
        except ValidationError as e:
            logger.warning("clipboard_send_validation_failed", error=str(e))
            return {"error": f"Validation failed: {e}"}

        from utils.db import get_pool

        try:
            pool = await get_pool()
        except Exception as e:
            logger.error("db_connection_failed", error=str(e))
            return {"error": f"Database unreachable: {e}"}

        row = await pool.fetchrow(
            "INSERT INTO mcp_clipboard (source, content, metadata) "
            "VALUES ($1, $2, $3::jsonb) RETURNING id, source, created_at",
            msg.source,
            msg.content,
            json.dumps(msg.metadata or {}),
        )
        logger.info("clipboard_send", id=row["id"], source=source)
        return {
            "id": row["id"],
            "source": row["source"],
            "created_at": row["created_at"].isoformat(),
        }

    @mcp.tool()
    async def clipboard_receive(source: str | None = None, limit: int = 5) -> dict:
        """Read recent messages from the MCP clipboard.

        Args:
            source: Optional filter — only return messages from this source.
            limit: Max number of messages to return (default 5).
        """
        from utils.db import get_pool

        try:
            pool = await get_pool()
        except Exception as e:
            logger.error("db_connection_failed", error=str(e))
            return {"error": f"Database unreachable: {e}"}

        if source:
            rows = await pool.fetch(
                "SELECT id, content, source, metadata, created_at "
                "FROM mcp_clipboard WHERE source = $1 "
                "ORDER BY created_at DESC LIMIT $2",
                source,
                limit,
            )
        else:
            rows = await pool.fetch(
                "SELECT id, content, source, metadata, created_at "
                "FROM mcp_clipboard ORDER BY created_at DESC LIMIT $1",
                limit,
            )

        return {
            "messages": [
                {
                    "id": r["id"],
                    "content": r["content"],
                    "source": r["source"],
                    "metadata": json.loads(r["metadata"]) if isinstance(r["metadata"], str) else dict(r["metadata"]),
                    "created_at": r["created_at"].isoformat(),
                }
                for r in rows
            ]
        }

    @mcp.tool()
    async def clipboard_clear(keep_last: int = 2, confirm: str = "") -> dict:
        """Delete old messages from the MCP clipboard, keeping the most recent ones.

        Args:
            keep_last: Number of recent messages to keep (minimum 2).
            confirm: Must be 'yes_delete' to execute.
        """
        if confirm != "yes_delete":
            return {"error": "Safety check: pass confirm='yes_delete' to execute"}

        if keep_last < 2:
            keep_last = 2

        from utils.db import get_pool

        try:
            pool = await get_pool()
        except Exception as e:
            logger.error("db_connection_failed", error=str(e))
            return {"error": f"Database unreachable: {e}"}

        result = await pool.execute(
            "DELETE FROM mcp_clipboard WHERE id NOT IN "
            "(SELECT id FROM mcp_clipboard ORDER BY created_at DESC LIMIT $1)",
            keep_last,
        )
        deleted = int(result.split()[-1])
        logger.info("clipboard_clear", deleted=deleted, kept=keep_last)
        return {"deleted_count": deleted, "kept": keep_last}