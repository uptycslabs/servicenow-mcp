"""Logging configuration for the ServiceNow MCP server."""

import logging
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOG_DIR = _PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "servicenow_mcp.log"

_configured = False


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger to write to both stderr and logs/servicenow_mcp.log.

    Safe to call multiple times; subsequent calls only update the level.
    """
    global _configured

    root = logging.getLogger()
    root.setLevel(level)

    if _configured:
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    _configured = True
