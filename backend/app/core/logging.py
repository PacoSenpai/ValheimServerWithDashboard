"""Configuración de logging estructurado."""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from logging import LogRecord


class JsonFormatter(logging.Formatter):
    def format(self, record: LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created).isoformat(timespec="seconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key, val in record.__dict__.items():
            if key in {"args", "asctime", "created", "exc_info", "exc_text", "filename",
                       "funcName", "levelname", "levelno", "lineno", "module", "msecs",
                       "message", "msg", "name", "pathname", "process", "processName",
                       "relativeCreated", "stack_info", "thread", "threadName", "taskName"}:
                continue
            payload[key] = val
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    level = os.environ.get("VALHEIM_DASHBOARD_LOG_LEVEL", "INFO").upper()
    root = logging.getLogger()
    root.setLevel(level)

    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(stream=sys.stderr)
    if os.environ.get("VALHEIM_DASHBOARD_LOG_JSON") == "1":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-7s %(name)s %(message)s",
                              datefmt="%H:%M:%S")
        )
    root.addHandler(handler)

    for noisy in ("apscheduler.scheduler", "apscheduler.executors.default",
                  "sqlalchemy.engine", "asyncio", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
