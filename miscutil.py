# miscutil.py
import os
import sys
import shutil
from datetime import datetime
from logger import setup_logger

logger = None  # Logger will be set up in preprocess

def get_dwg_files_in_directory(directory):
    dwg_files = [file for file in os.listdir(directory) if file.endswith(".dwg")]
    if not dwg_files:
        sys.exit('THERE ARE NO FILES')
    return dwg_files

def safe_remove(path):
    try:
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
    except Exception as exc:
        if logger:
            logger.error("%s is in use or cannot be removed: %s", path, exc)
        else:
            print(f"{path} is in use or cannot be removed: {exc}")

def remove_previous_preprocess(base_path):
    originals_path = os.path.join(base_path, "originals")
    if os.path.exists(originals_path):
        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)
            if item != "originals":
                safe_remove(item_path)
        for file in os.listdir(originals_path):
            shutil.copy(os.path.join(originals_path, file), os.path.join(base_path, file))
        safe_remove(originals_path)
        if logger:
            logger.info("TIDY COMPLETE")
        else:
            print("TIDY COMPLETE")

def create_directory(path):
    if not os.path.exists(path):
        try:
            os.mkdir(path)
        except Exception as exc:
            if logger:
                logger.error("Failed to create %s: %s", path, exc)
            else:
                print(f"Failed to create {path}: {exc}")

def cleanup_old_logs(log_dir):
    """Rename existing log directory and create a fresh one."""
    if os.path.exists(log_dir):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        os.rename(log_dir, f"{log_dir}_backup_{timestamp}")
    create_directory(log_dir)

def preprocess():
    global logger
    base_path = os.getcwd()
    remove_previous_preprocess(base_path)
    logger = setup_logger("MISC_UTIL")
    logger.info("Starting preprocessing")
    dwg_files = get_dwg_files_in_directory(base_path)
    for folder in ["scripts", "originals", "derevitized"]:
        create_directory(os.path.join(base_path, folder))
    cleanup_old_logs(os.path.join(base_path, "logs"))
    
    logger.info("COPYING %d FILES", len(dwg_files))
    for file_name in dwg_files:
        src_path = os.path.join(base_path, file_name)
        shutil.copy(src_path, os.path.join(base_path, "originals", file_name))
        shutil.copy(src_path, os.path.join(base_path, "derevitized", file_name))
        os.remove(src_path)
    
    logger.info("Preprocessing complete")
