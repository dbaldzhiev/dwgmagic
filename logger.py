import logging
import os
from config import log_encoding, log_level

def setup_logger(name, log_dir="logs"):
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level))

    file_handler = logging.FileHandler(os.path.join(log_dir, f"{name}.log"), encoding=log_encoding)
    file_handler.setLevel(getattr(logging, log_level))

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    return logger
