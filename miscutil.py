import os
import sys
import shutil

def get_dwg_files_in_directory(path):
    output = [file for file in os.listdir(path) if file.endswith(".dwg")]
    if len(output) < 1:
        sys.exit('THERE ARE NO FILES')
    return output

def removePrevPreprocess():
    path = os.getcwd()
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

# ordering the folder so it has the folders scripts, originals and derevitized and copying the dwgs in the proper places
def preprocess():
    path = os.getcwd()
    fns = get_dwg_files_in_directory(os.getcwd())
    if not os.path.exists(str(path + "/scripts")):
        try:
            os.mkdir("scripts")
        except:
            print("Scripts folder already exists")

    if not os.path.exists(str(path + "/originals")):
        try:
            os.mkdir("originals")
        except:
            print("Originals folder already exists")

    if not os.path.exists(str(path + "/derevitized")):
        try:
            os.mkdir("derevitized")
        except:
            print("Derevitized folder already exists")
    
    print("\t  +++++ COPYING {0} FILES +++++".format(len(fns)))
    for fn in fns:
        #print("COPYING " + fn)
        shutil.copy(path + "/" + fn, path + "/originals/" + fn)
        shutil.copy(path + "/" + fn, path + "/derevitized/" + fn)
        os.remove(path + "/" + fn)

