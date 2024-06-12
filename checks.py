import config as cfg
import shlex
import subprocess as sp
import sys
import os

def accVersion():
        for key in cfg.accpathv:
            if os.path.exists(cfg.accpathv[key]):
                return cfg.accpathv[key]
        sys.exit('Cannot find accoreconsole.exe')

def checks():
        command = "\"{acc}\" /s \"{path}/trustedFolderCheck.scr\"".format(acc=accVersion(), path=cfg.paths["dmm"])
        print("──────────────────────────────────────────────")
        print("+++++ ACCORECONSOLE PATH: {} ++++++      ".format(accVersion()))
        print("+++++ CHECKING TRUSTED FOLDER: {} ++++++ ".format(command))
        process = sp.Popen(shlex.split(command), stdout=sp.PIPE, shell=True, encoding='utf-16-le', errors='replace')
        output, err = process.communicate()
        #print(output)
        if "Unable to load C:\\dwgmagic2\\tectonica.dll assembly." in output:
            print("!!!! TRUSTED FOLDER IS NOT SET UP !!!!")
        print("──────────────────────────────────────────────")
