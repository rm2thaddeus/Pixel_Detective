"""
Logging setup for the Pixel Detective app.
"""
import logging
import sys
import os
from datetime import datetime

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Configure the root logger
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s.%(msecs)03d] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"logs/pixel_detective_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", encoding='utf-8')
    ]
)

# Create logger
logger = logging.getLogger("pixel_detective")
logger.setLevel(logging.INFO)

# Export logger
__all__ = ["logger"] 