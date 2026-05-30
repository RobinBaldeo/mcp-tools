import os
import time

_start_time = time.monotonic()


def register(mcp):
    from utils.config_loader import load_config

    cfg = load_config()

    @mcp.tool()
    def ping() -> dict:
        """Health check — returns server status, uptime, version, and env confirmation."""
        env_keys = [k for k in os.environ if k.isupper() and not k.startswith("_")]
        return {
            "status": "ok",
            "uptime_seconds": round(time.monotonic() - _start_time, 2),
            "server": cfg.server.name,
            "version": cfg.server.version,
            "env_vars_loaded": len(env_keys),
            "port": cfg.port,
        }
