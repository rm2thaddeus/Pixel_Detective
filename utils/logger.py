"""
Logging setup for the Pixel Detective app.
"""
import logging
import sys
import os
from logging.handlers import RotatingFileHandler

# Determine log level from environment variable, default to INFO
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

# Create logs directory if it doesn't exist
LOGS_DIR = "logs"
os.makedirs(LOGS_DIR, exist_ok=True)

# Create a professional, colored formatter
LOG_FORMAT = "%(asctime)s - %(name)s - [%(levelname)s] - (%(filename)s:%(lineno)d) - %(message)s"
# For file logging, a simple format is often better
FILE_LOG_FORMAT = "%(asctime)s - %(name)s - [%(levelname)s] - (%(filename)s:%(lineno)d) - %(message)s"

class ColorFormatter(logging.Formatter):
    """A class to add color to log messages."""
    GREY = "\x1b[38;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    GREEN = "\x1b[32;20m"
    RESET = "\x1b[0m"

    FORMATS = {
        logging.DEBUG: GREEN + LOG_FORMAT + RESET,
        logging.INFO: GREY + LOG_FORMAT + RESET,
        logging.WARNING: YELLOW + LOG_FORMAT + RESET,
        logging.ERROR: RED + LOG_FORMAT + RESET,
        logging.CRITICAL: BOLD_RED + LOG_FORMAT + RESET,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

# --- Stream Handler (Console) ---
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(ColorFormatter())

# --- File Handler (Rotating) ---
# Use a single, rotating log file to prevent clutter
file_handler = RotatingFileHandler(
    os.path.join(LOGS_DIR, "frontend.log"),
    maxBytes=5 * 1024 * 1024,  # 5 MB
    backupCount=2,
    encoding='utf-8'
)
file_handler.setFormatter(logging.Formatter(FILE_LOG_FORMAT))

# --- Configure Root Logger ---
# Clear existing handlers to prevent duplicate logs from basicConfig
logging.getLogger().handlers = []
logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    handlers=[stream_handler, file_handler]
)

def get_logger(name: str) -> logging.Logger:
    """
    Retrieves a logger instance with the specified name.
    The logger will be configured with the application's handlers.
    """
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    # The handlers are already on the root logger, so child loggers will propagate to them.
    # We don't need to add handlers to each new logger instance.
    return logger

# Export a default logger for convenience, but get_logger is preferred
logger = get_logger("pixel_detective_default")

# Export logger
__all__ = ["logger"] 