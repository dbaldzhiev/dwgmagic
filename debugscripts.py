import os
import shutil
import sys
import miscutil
import config as cfg
import shlex
import subprocess as sp

def trustedFolderCheck():
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

            
        #else:
            #print("TRUSTED FOLDER IS PROPERLY SET UP")
    
def removePrevPP(path):
    # Check if originals folder exists
    if os.path.exists(str(path + "/originals")):
        # Loop through all files in path
        for e in os.listdir(path):
            # Check if file
            if os.path.isfile("{0}/{1}".format(path, e)):
                # Try to remove file
                try:
                    os.remove("{0}/{1}".format(path, e))
                # Catch error
                except:
                    print("{0} is is use! CAN'T REMOVE".format(e))
                    sys.exit(1)
            # Check if directory
            if os.path.isdir("{0}/{1}".format(path, e)):
                # Check if directory is not originals
                if e != "originals":
                    # Try to remove directory
                    try:
                        shutil.rmtree(("{0}/{1}".format(path, e)))
                    # Catch error
                    except:
                        print("{0} is is use! CAN'T REMOVE".format(e))
                        sys.exit(1)

        # Copy all files from originals to path
        ([shutil.copy("{p}/originals/{f}".format(p=path, f=file), "{p}/{f}".format(p=path, f=file)) for file in
          os.listdir("{0}/originals".format(path))])
        # Try to remove originals directory
        try:
            shutil.rmtree("{0}/originals".format(path))
        # Catch error
        except:
            sys.exit(1)
        print("\t  +++++ TIDY COMPLETE +++++")
