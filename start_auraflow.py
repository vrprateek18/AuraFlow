"""
AuraFlow — Move naturally. Control effortlessly.
Premium Unified Windows & macOS Gesture Control Application
"""
import sys
import os

# Add windows directory to sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
windows_dir = os.path.join(root_dir, "windows")
if windows_dir not in sys.path:
    sys.path.insert(0, windows_dir)

from auramotion_windows.app import main

if __name__ == "__main__":
    main()
