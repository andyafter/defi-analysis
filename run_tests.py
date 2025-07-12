#!/usr/bin/env python3
"""
Run all unit tests for the Uniswap V3 analysis project.
"""

import sys
import unittest
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_dependencies():
    """Check if required dependencies are installed."""
    missing_deps = []
    
    try:
        import web3
    except ImportError:
        missing_deps.append('web3')
    
    try:
        import matplotlib
    except ImportError:
        missing_deps.append('matplotlib')
    
    try:
        import pandas
    except ImportError:
        missing_deps.append('pandas')
    
    try:
        import numpy
    except ImportError:
        missing_deps.append('numpy')
    
    if missing_deps:
        print("\n" + "="*60)
        print("WARNING: Missing dependencies detected!")
        print("="*60)
        print(f"Missing packages: {', '.join(missing_deps)}")
        print("\nTo install all dependencies, run:")
        print("  pip install -r requirements.txt")
        print("\nSome tests may be skipped due to missing dependencies.")
        print("="*60 + "\n")
        return False
    return True

if __name__ == '__main__':
    # Check dependencies
    deps_ok = check_dependencies()
    
    # Discover and run all tests
    loader = unittest.TestLoader()
    start_dir = 'tests'
    
    # If dependencies are missing, only run tests that don't require them
    if not deps_ok:
        # Just run uniswap_v3 tests which don't require web3
        suite = loader.loadTestsFromName('tests.test_uniswap_v3')
        print("Running only tests that don't require external dependencies...\n")
    else:
        suite = loader.discover(start_dir, pattern='test_*.py')
        print("Running all tests...\n")
    
    # Run tests with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed.")
    
    if not deps_ok:
        print("\n⚠️  Note: Full test suite requires all dependencies to be installed.")
    
    print("="*60)
    
    # Exit with error code if tests failed
    sys.exit(0 if result.wasSuccessful() else 1) 