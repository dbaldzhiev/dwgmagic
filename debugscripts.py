import miscutil
import config as cfg
import shlex
import subprocess as sp

def checks():
        command = "\"{acc}\" /s \"{path}/trustedFolderCheck.scr\"".format(acc=miscutil.accVersion(), path=cfg.paths["dmm"])
        print("\t  ──────────────────────────────────────────────")
        print("\t  +++++ ACCORECONSOLE PATH: {} ++++++      ".format(miscutil.accVersion()))
        print("\t  +++++ CHECKING TRUSTED FOLDER: {} ++++++ ".format(command))
        process = sp.Popen(shlex.split(command), stdout=sp.PIPE, shell=True, encoding='utf-16-le', errors='replace')
        output, err = process.communicate()
        #print(output)
        if "Unable to load C:\\dwgmagic2\\tectonica.dll assembly." in output:
            print("\t  !!!! TRUSTED FOLDER IS NOT SET UP !!!!")
        print("\t  ──────────────────────────────────────────────")
