"""
FarmerVerify AI - Logging Configuration
Uses loguru for structured, colorful logging with file rotation.
"""

import sys
from pathlib import Path
from loguru import logger

# Remove default handler
logger.remove()

# Create log directory
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Console handler - colorful, concise
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="DEBUG",
    colorize=True,
)

# File handler - detailed, rotating
logger.add(
    LOG_DIR / "farmerverify.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
    compression="zip",
)

# Error-only file handler
logger.add(
    LOG_DIR / "errors.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name}:{function}:{line} - {message}\n{exception}",
    level="ERROR",
    rotation="5 MB",
    retention="30 days",
    compression="zip",
)


def setup_logger():
    """Initialize logger (already done at import time). Returns logger instance."""
    return logger


def get_logger(name: str = None):
    """
    Get a logger instance. For compatibility across all modules.
    Loguru uses a single global logger, so the name is logged via bind().
    """
    if name:
        return logger.bind(module=name)
    return logger