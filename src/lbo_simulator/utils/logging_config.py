"""Logging configuration with audit trail IDs."""

from __future__ import annotations

import uuid

from loguru import logger


def get_audit_id() -> str:
    """Generate a unique audit trail ID."""
    return str(uuid.uuid4())[:8]


def setup_logging(audit_id: str | None = None, log_file: str | None = None) -> str:
    """Setup structured logging with audit trail.

    Returns:
        The audit ID used for this session.
    """
    if audit_id is None:
        audit_id = get_audit_id()

    # Remove default handler
    logger.remove()

    # Console handler
    logger.add(
        lambda msg: print(msg, end=""),
        format=f"[{{time:YYYY-MM-DD HH:mm:ss}}] [AUDIT:{audit_id}] [{{level}}] {{message}}",
        level="INFO",
    )

    # File handler
    if log_file:
        logger.add(
            log_file,
            format=f"[{{time:YYYY-MM-DD HH:mm:ss}}] [AUDIT:{audit_id}] [{{level}}] {{file}}:{{line}} - {{message}}",
            level="DEBUG",
        )

    logger.info(f"Logging initialized with audit ID: {audit_id}")
    return audit_id
