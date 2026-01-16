"""Frontend log ingestion endpoint."""

import logging
import re
import sys
from typing import Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter

from ..dependencies import CurrentUser

# Configure frontend logger with stdout handler
logger = logging.getLogger("frontend")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[FRONTEND] %(levelname)s %(message)s"))
    logger.addHandler(handler)

router = APIRouter()

def sanitize_log_message(msg: str) -> str:
    """Remove newlines and control characters to prevent log injection."""
    return re.sub(r'[\r\n\x00-\x1f\x7f-\x9f]', ' ', msg)


class LogEntry(BaseModel):
    level: str = Field(max_length=50)
    message: str = Field(max_length=1_000_000)  # 1MB per message
    timestamp: str = Field(max_length=200)
    context: Optional[dict] = None


class IngestLogsRequest(BaseModel):
    entries: list[LogEntry] = Field(max_length=10_000)
    device_id: Optional[str] = Field(default=None, max_length=1000)
    session_id: Optional[str] = Field(default=None, max_length=1000)


@router.post(
    "/ingest",
    status_code=204,
    summary="Ingest frontend logs",
    description="Receive log entries from the frontend and write them to backend logs.",
)
async def ingest_logs(request: IngestLogsRequest, user: CurrentUser):
    """Write frontend log entries to backend logs with [FRONTEND] marker."""
    device_info = ""
    if request.device_id:
        device_info = f" device={request.device_id}"
    if request.session_id:
        device_info += f" session={request.session_id}"

    for entry in request.entries:
        context_str = ""
        if entry.context:
            context_str = f" {entry.context}"

        safe_message = sanitize_log_message(entry.message)
        log_message = f"{device_info} [{entry.timestamp}] {safe_message}{context_str}"

        level = entry.level.lower()
        if level == "error":
            logger.error(log_message)
        elif level == "warn":
            logger.warning(log_message)
        elif level == "debug":
            logger.debug(log_message)
        else:
            logger.info(log_message)
