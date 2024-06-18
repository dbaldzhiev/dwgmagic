# checks.py
import config as cfg
import shlex
import subprocess as sp
import sys
import os
from logger import setup_logger

def acc_version():
    for path in cfg.accpathv.values():
        if os.path.exists(path):
            return path
    sys.exit('Cannot find accoreconsole.exe')

def checks(log_dir=None):
    log_dir = log_dir or os.path.join(cfg.DMM_PATH, "logs")
    logger = setup_logger("CHECKS", log_dir=log_dir)

    acc_path = acc_version()
    command = f"\"{acc_path}\" /s \"{cfg.DMM_PATH}/trustedFolderCheck.scr\""

    logger.info("ACCORECONSOLE PATH: %s", acc_path)
    logger.info("CHECKING TRUSTED FOLDER: %s", command)

    process = sp.Popen(shlex.split(command), stdout=sp.PIPE, shell=True, encoding='utf-16-le', errors='replace')
    output, _ = process.communicate()

    if "Unable to load C:\\dwgmagic2\\tectonica.dll assembly." in output:
        sys.exit("TRUSTED FOLDER IS NOT SET UP")

    logger.info("Trusted folder check complete")
