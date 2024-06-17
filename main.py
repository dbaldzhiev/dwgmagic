import os
import sys
import merger as m
import miscutil as mu
import checks
from rich.console import Console
from rich.progress import track

def display_title_bar():
    print("\t  ╭──────────────────────────────────────────────╮")
    print("\t  │        🪄  DWGMAGIC IS STARTING  🏰          │")
    print("\t  ├──────────────────────────────────────────────┤")
    print("\t  │        TECTONICA - Dimitar Baldzhiev         │")
    print("\t  ╰──────────────────────────────────────────────╯")

def main(path):
    log_dir = os.path.join(path, "logs")
    mu.cleanup_old_logs(log_dir)  # Move old logs to a backup directory before setting up new logger
    display_title_bar()
    checks.checks()
    os.chdir(path)
    mu.preprocess(log_dir=log_dir)
    m.Project(log_dir=log_dir)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("ERROR! No path provided!")
    main(sys.argv[1])
