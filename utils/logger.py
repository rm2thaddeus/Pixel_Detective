"""
Logging setup for the Pixel Detective app.
"""
import logging

def setup_logger():
    """
    Set up logging configuration.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    return logging.getLogger(__name__)

# Create a logger instance
logger = setup_logger() 