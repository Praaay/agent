#!/usr/bin/env python3
"""
Test script that demonstrates how Bugfree should catch errors from other Python processes.
"""

import subprocess
import sys
import asyncio
from datetime import datetime

async def test_bugfree_error_detection():
    """Test if Bugfree can detect errors from other Python processes."""
    
    print("🧪 Testing Bugfree Error Detection")
    print("=" * 50)
    
    # Run test_errors.py and capture its output
    print("1. Running test_errors.py...")
    try:
        result = subprocess.run(
            [sys.executable, "test_errors.py"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        print(f"Exit code: {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        
        if result.returncode != 0:
            print("✅ Error detected in test_errors.py")
            print(f"Error: {result.stderr.strip()}")
            
            # Now test if Bugfree system can analyze this error
            print("\n2. Testing Bugfree error analysis...")
            await test_bugfree_analysis(result.stderr.strip())
        else:
            print("❌ No error detected (unexpected)")
            
    except subprocess.TimeoutExpired:
        print("❌ test_errors.py timed out")
    except Exception as e:
        print(f"❌ Error running test_errors.py: {e}")

async def test_bugfree_analysis(error_message: str):
    """Test if Bugfree can analyze the captured error."""
    
    # This would normally connect to the running Bugfree system
    # For now, we'll simulate what should happen
    
    print(f"Error to analyze: {error_message}")
    
    # Simulate error analysis
    if "NameError" in error_message:
        print("✅ Bugfree should detect: NAME_ERROR")
        print("💡 Suggested fix: Define the variable before using it")
    elif "TypeError" in error_message:
        print("✅ Bugfree should detect: TYPE_ERROR")
        print("💡 Suggested fix: Check data types before operations")
    elif "ImportError" in error_message:
        print("✅ Bugfree should detect: IMPORT_ERROR")
        print("💡 Suggested fix: Install missing module or check import path")
    else:
        print("❓ Unknown error type")
    
    print("\n🎯 Expected Bugfree Behavior:")
    print("- Detect the NameError from test_errors.py")
    print("- Create an ErrorContext with proper error type")
    print("- Generate fix suggestions")
    print("- Display them in the VS Code extension")

if __name__ == "__main__":
    asyncio.run(test_bugfree_error_detection()) 