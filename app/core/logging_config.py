"""Logging configuration using loguru."""

import sys
from loguru import logger


def setup_logging(debug: bool = False) -> None:
    """Configure application logging."""
    logger.remove()  # Remove default handler

    log_level = "DEBUG" if debug else "INFO"
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    logger.add(sys.stderr, format=log_format, level=log_level, colorize=True)
    logger.add(
        "logs/idp_pipeline_{time:YYYY-MM-DD}.log",
        format=log_format,
        level="DEBUG",
        rotation="1 day",
        retention="7 days",
        compression="zip",
    )
