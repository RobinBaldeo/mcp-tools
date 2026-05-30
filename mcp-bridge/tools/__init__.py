import importlib
import pkgutil
from pathlib import Path

import structlog

logger = structlog.get_logger()


def register_all(mcp):
    package_dir = Path(__file__).resolve().parent
    for module_info in pkgutil.iter_modules([str(package_dir)]):
        if module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"tools.{module_info.name}")
        if hasattr(module, "register"):
            module.register(mcp)
            logger.info("tool_module_registered", module=module_info.name)
