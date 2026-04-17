# -*- coding: utf-8 -*-
import os
import datetime
import logging
from pathlib import Path

from rcp_task_acquisition.utils.constants import RAW_DATA_DIR



def get_logger(name: str = "cart") -> logging.Logger:
    """
    Get a logger with both file and console output.

    Args:
        name (str): Logger name (recommended: module name)

    Returns:
        logging.Logger: Configured logger instance
    """
    # log_dir = Path(RAW_DATA_DIR+ "/logs") #Path("/home/rcp/task-acquisition/logs")
    date_string = datetime.datetime.utcnow().strftime("%Y%m%d")
    log_str = os.path.join(RAW_DATA_DIR, date_string)
    log_dir = Path(log_str)
    # Ensure the log directory exists
    log_dir.mkdir(parents=True, exist_ok=True)

    # Log file name
    log_filename =  os.path.join(log_dir, f'{date_string}_log.log')
    if not os.path.exists(log_filename):
        open(log_filename,'w').close()

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Record all levels by default

    # Avoid adding duplicate handlers
    if not logger.handlers:
        # File handler (write to file)
        file_handler = logging.FileHandler(log_filename, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        # Console handler (output to terminal)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%H:%M:%S"
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
