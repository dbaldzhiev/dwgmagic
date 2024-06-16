import os
import sys
import shutil

def get_dwg_files_in_directory(directory):
    """Return a list of .dwg files in the specified directory."""
    dwg_files = [file for file in os.listdir(directory) if file.endswith(".dwg")]
    if not dwg_files:
        sys.exit('THERE ARE NO FILES')
    return dwg_files

def safe_remove(path):
    """Safely remove a file or directory."""
    try:
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
    except Exception as exc:
        print(f"{path} is in use or cannot be removed: {exc}")
        sys.exit(1)

def remove_previous_preprocess(base_path):
    """Remove all files and directories except the originals folder and restore files from originals."""
    originals_path = os.path.join(base_path, "originals")
    
    if os.path.exists(originals_path):
        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)
            if item != "originals":
                safe_remove(item_path)
        
        for file in os.listdir(originals_path):
            shutil.copy(os.path.join(originals_path, file), os.path.join(base_path, file))
        
        safe_remove(originals_path)
        print("+++++ TIDY COMPLETE +++++")

def create_directory(path):
    """Create a directory if it does not exist."""
    if not os.path.exists(path):
        try:
            os.mkdir(path)
        except Exception as exc:
            print(f"Failed to create {path}: {exc}")

def preprocess():
    """Main preprocessing function."""
    print("──────────────────────────────────────────────")
    
    base_path = os.getcwd()
    remove_previous_preprocess(base_path)
    dwg_files = get_dwg_files_in_directory(base_path)
    
    # Create required directories
    for folder in ["scripts", "originals", "derevitized", "logs"]:
        create_directory(os.path.join(base_path, folder))
    
    print(f"+++++ COPYING {len(dwg_files)} FILES +++++")
    for file_name in dwg_files:
        src_path = os.path.join(base_path, file_name)
        shutil.copy(src_path, os.path.join(base_path, "originals", file_name))
        shutil.copy(src_path, os.path.join(base_path, "derevitized", file_name))
        os.remove(src_path)
    
    print("──────────────────────────────────────────────")
