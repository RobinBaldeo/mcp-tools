from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(_ROOT / ".env")


@dataclass
class ServerMeta:
    name: str = "mcp-bridge"
    version: str = "0.0.0"
    description: str = ""


@dataclass
class GrokConfig:
    model: str = "grok-4-1-fast-non-reasoning"


@dataclass
class Config:
    server: ServerMeta = field(default_factory=ServerMeta)
    endpoints: dict = field(default_factory=dict)
    features: dict = field(default_factory=dict)
    grok: GrokConfig = field(default_factory=GrokConfig)
    port: int = 8000


def load_config(path: Path | None = None) -> Config:
    path = path or _ROOT / "config.yaml"
    raw: dict = {}
    if path.exists():
        with open(path) as f:
            raw = yaml.safe_load(f) or {}

    server_raw = raw.get("server", {})
    server = ServerMeta(
        name=server_raw.get("name", "mcp-bridge"),
        version=server_raw.get("version", "0.0.0"),
        description=server_raw.get("description", ""),
    )

    grok_raw = raw.get("grok", {})
    grok = GrokConfig(
        model=grok_raw.get("model", "grok-4-1-fast-non-reasoning"),
    )

    return Config(
        server=server,
        endpoints=raw.get("endpoints", {}),
        features=raw.get("features", {}),
        grok=grok,
        port=int(os.environ.get("PORT", 8000)),
    )
