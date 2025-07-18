#!/usr/bin/env python3
"""
Run all mathematical validation tests and report any issues found.
"""

import sys
import subprocess
import asyncio
from pathlib import Path

def run_test_file(test_file):
    """Run a single test file and return results."""
    print(f"\n{'='*60}")
    print(f"Running {test_file}")
    print('='*60)
    
    result = subprocess.run(
        [sys.executable, test_file],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
        print("\nSTDOUT:")
        print(result.stdout)
        print("\nSTDERR:")
        print(result.stderr)
    
    return result.returncode == 0

def main():
    """Run all math validation tests."""
    print("🧮 Mathematical Validation Test Suite")
    print("====================================")
    print("Testing for:")
    print("- Negative liquidity values")
    print("- Incorrect fee calculations")
    print("- Impermanent loss accuracy")
    print("- Position calculation errors")
    print("- Edge cases and boundaries")
    
    tests_dir = Path(__file__).parent
    
    # Run the comprehensive math tests
    all_passed = run_test_file(tests_dir / "test_mathematics_validation.py")
    
    # Also run existing related tests
    print("\nRunning existing test suites...")
    
    test_files = [
        "test_uniswap_v3.py",
        "test_analysis.py"
    ]
    
    for test_file in test_files:
        test_path = tests_dir / test_file
        if test_path.exists():
            passed = run_test_file(test_path)
            all_passed = all_passed and passed
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ All mathematical validations passed!")
        print("The calculations appear to be correct.")
    else:
        print("❌ Some mathematical validations failed!")
        print("Please review the errors above.")
    print("="*60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main()) 