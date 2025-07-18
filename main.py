# main.py
import os
import argparse
import merger as m
import miscutil as mu
import checks
import config as cfg

def display_title_bar():
    title_bar = """
    ╭──────────────────────────────────────────────╮
    │                   DWGMAGIC                   │
    ├──────────────────────────────────────────────┤
    │        TECTONICA - Dimitar Baldzhiev         │
    ╰──────────────────────────────────────────────╯
    """
    print(title_bar)

def parse_args():
    parser = argparse.ArgumentParser(description="DWGMAGIC Toolset")
    parser.add_argument("path", nargs="?", help="Path to the project directory")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--gui", action="store_true", help="Launch GUI")
    parser.add_argument("--log-dir", default="logs", help="Directory for output logs")
    return parser.parse_args()

def main(path, verbose, log_dir="logs"):
    cfg.verbose = verbose
    os.chdir(path)
    display_title_bar()
    checks.checks(log_dir=log_dir)
    mu.cleanup_old_logs(os.path.join(os.getcwd(), log_dir))
    mu.preprocess()
    m.Project(log_dir=log_dir)

if __name__ == "__main__":
    args = parse_args()
    if args.gui:
        import gui
        gui.launch()
    else:
        if not args.path:
            print("Path argument is required unless --gui is used")
        else:
            main(args.path, args.verbose, args.log_dir)
