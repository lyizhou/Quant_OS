"""Unified logging configuration for the application."""

import sys
import uuid
from contextvars import ContextVar
from typing import Optional

from loguru import logger

# Context variable for trace ID (for request tracing)
trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)


def get_trace_id() -> str:
    """Get current trace ID or generate a new one."""
    trace_id = trace_id_var.get()
    if trace_id is None:
        trace_id = str(uuid.uuid4())[:8]
        trace_id_var.set(trace_id)
    return trace_id


def set_trace_id(trace_id: str) -> None:
    """Set trace ID for current context."""
    trace_id_var.set(trace_id)


def clear_trace_id() -> None:
    """Clear trace ID from current context."""
    trace_id_var.set(None)


def setup_logging(level: str = "INFO", json_format: bool = False) -> None:
    """Configure logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: If True, output logs in JSON format
    """
    # Fix for Windows Unicode output
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    # Remove default handler
    logger.remove()

    # Custom format with trace ID
    if json_format:
        # JSON format for production
        log_format = (
            "{"
            '"time": "{time:YYYY-MM-DD HH:mm:ss.SSS}", '
            '"level": "{level}", '
            '"module": "{module}", '
            '"function": "{function}", '
            '"line": {line}, '
            '"trace_id": "{extra[trace_id]}", '
            '"message": "{message}"'
            "}"
        )
    else:
        # Human-readable format for development
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<yellow>[{extra[trace_id]}]</yellow> | "
            "<level>{message}</level>"
        )

    # Add handler with trace ID injection
    logger.configure(
        handlers=[
            {
                "sink": sys.stdout,
                "format": log_format,
                "level": level,
                "colorize": not json_format,
            }
        ],
        # Inject trace_id into all log records
        patcher=lambda record: record["extra"].update(trace_id=get_trace_id()),
    )


def get_logger(module_name: str):
    """Get a logger instance for a specific module.

    Args:
        module_name: Name of the module (usually __name__)

    Returns:
        Logger instance bound to the module
    """
    return logger.bind(module=module_name)


# Initialize with default settings
setup_logging()
