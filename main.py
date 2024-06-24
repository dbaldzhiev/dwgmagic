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
    parser.add_argument("path", help="Path to the project directory")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    return parser.parse_args()

def main(path, verbose):
    cfg.verbose = verbose
    os.chdir(path)
    display_title_bar()
    checks.checks()
    mu.preprocess()
    m.Project()

if __name__ == "__main__":
    args = parse_args()
    main(args.path, args.verbose)
