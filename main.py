import os
import sys
import merger as m
import miscutil as mu
import checks

def display_title_bar():
    # Clears the terminal screen, and displays a title bar.

    print("\t  ╭──────────────────────────────────────────────╮")
    print("\t  │        🪄  DWGMAGIC IS STARTING  🏰           │")
    print("\t  ├──────────────────────────────────────────────┤")
    print("\t  │        TECTONICA - Dimitar Baldzhiev         │")
    print("\t  ╰──────────────────────────────────────────────╯")


def main(path):

    # Display the title bar.
    display_title_bar()
    checks.checks()     

    # Change the current working directory.
    os.chdir(path)

    # Preprocess the file.
    mu.preprocess()

    # Run the project.
    m.Project()

if __name__ == "__main__":
    try:
        # Print the path to be processed.
        print("+++++ TARGET PROJECT: {}".format(sys.argv[1]))
    except:
        sys.exit("ERROR! No path provided!")
    main(sys.argv[1])

