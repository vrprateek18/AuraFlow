"""
AuraFlow — Move naturally. Control effortlessly.
Premium Unified Windows & macOS Gesture Control Application
"""
import sys
import os

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auramotion_windows.app import main

if __name__ == "__main__":
    main()
