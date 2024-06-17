import config as cfg
import shlex
import subprocess as sp
import sys
import os

def acc_version():
    for path in cfg.accpathv.values():
        if os.path.exists(path):
            return path
    sys.exit('Cannot find accoreconsole.exe')

def checks():
    acc_path = acc_version()
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
