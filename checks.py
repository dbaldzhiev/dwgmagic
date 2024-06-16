import config as cfg
import shlex
import subprocess as sp
import sys
import os

def accVersion():
    """
    Returns the path to accoreconsole.exe if it exists, exits otherwise.
    """
    for key in cfg.accpathv:
        if os.path.exists(cfg.accpathv[key]):
            return cfg.accpathv[key]
    sys.exit('Cannot find accoreconsole.exe')

def checks():
    """
    Checks if the trusted folder is set up by executing a script using accoreconsole.exe.
    """
    acc_path = accVersion()
    command = f"\"{acc_path}\" /s \"{cfg.paths['dmm']}/trustedFolderCheck.scr\""
    
    print("──────────────────────────────────────────────")
    print(f"+++++ ACCORECONSOLE PATH: {acc_path} ++++++")
    print(f"+++++ CHECKING TRUSTED FOLDER: {command} ++++++")
    
    process = sp.Popen(shlex.split(command), stdout=sp.PIPE, shell=True, encoding='utf-16-le', errors='replace')
    output, err = process.communicate()
    
    if "Unable to load C:\\dwgmagic2\\tectonica.dll assembly." in output:
        sys.exit("!!!! TRUSTED FOLDER IS NOT SET UP !!!!")
    
    print("──────────────────────────────────────────────")

if __name__ == "__main__":
    checks()
