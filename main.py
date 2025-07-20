# main.py
import os
import argparse
from rich.console import Console
import merger as m
import miscutil as mu
import checks
import config as cfg

console = Console()

def display_title_bar():
    console.print("╭──────────────────────────────────────────────╮", style="cyan")
    console.print("│                   [bold magenta]DWGMAGIC[/bold magenta]                   │")
    console.print("├──────────────────────────────────────────────┤", style="cyan")
    console.print("│        [italic]TECTONICA - Dimitar Baldzhiev[/italic]         │")
    console.print("╰──────────────────────────────────────────────╯", style="cyan")

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
