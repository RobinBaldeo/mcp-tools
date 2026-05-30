import structlog

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)

from starlette.responses import JSONResponse

from mcp.server.fastmcp import FastMCP
from utils.config_loader import load_config

logger = structlog.get_logger()
cfg = load_config()

app = FastMCP(
    name=cfg.server.name,
    host="0.0.0.0",
    port=cfg.port,
    stateless_http=True,
)

# Auto-discover and register all tool modules
from tools import register_all

register_all(app)

# Debug: log all registered tool names
tool_names = [t.name for t in app._tool_manager._tools.values()]
logger.info("registered_tools", tools=tool_names, count=len(tool_names))

logger.info(
    "server_ready",
    name=cfg.server.name,
    version=cfg.server.version,
    port=cfg.port,
)

if __name__ == "__main__":
    import uvicorn
    from starlette.routing import Route

    mcp_asgi = app.streamable_http_app()

    # Inject /health route for Railway healthcheck
    async def health(request):
        return JSONResponse({"status": "ok"})

    mcp_asgi.routes.insert(0, Route("/health", health))

    uvicorn.run(mcp_asgi, host="0.0.0.0", port=cfg.port)
