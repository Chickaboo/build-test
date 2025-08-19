#!/usr/bin/env python3

import os
import shutil
from pathlib import Path


def main():
    # Get the directory where this script is located
    script_dir = Path(__file__).parent

    print(f"cleaning: {script_dir}")

    # Define directories to clean
    built_dir = script_dir / "build"
    dist_dir = script_dir / "dist"

    # Remove contents of directories if they exist
    for directory in [built_dir, dist_dir]:
        if directory.exists():
            # Remove all contents but keep the directory
            for item in directory.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                    print(f"Removed directory: {item}")
                else:
                    item.unlink()
                    print(f"Removed file: {item}")
        else:
            print(f"Directory not found (skipping): {directory}")

    print("cleaned out all built stuff")


if __name__ == "__main__":
    main()
