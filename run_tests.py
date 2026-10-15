"""
AuraFlow — Universal Test Runner
Executes Windows test suite with proper path resolution.
"""
import sys
import os
import unittest

root_dir = os.path.dirname(os.path.abspath(__file__))
windows_dir = os.path.join(root_dir, "windows")
os.chdir(windows_dir)
if windows_dir not in sys.path:
    sys.path.insert(0, windows_dir)

loader = unittest.TestLoader()
suite = loader.discover("tests")
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
