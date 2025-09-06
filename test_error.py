#!/usr/bin/env python3
"""
Test file with intentional errors to demonstrate Bugfree system.
"""

# This will cause an ImportError
import nonexistent_module

# This will cause a NameError
undefined_variable = 42

def test_function():
    # This will cause a TypeError
    number = 42
    result = number()  # Trying to call an int as a function
    return result

if __name__ == "__main__":
    print("This will never be reached due to errors above") 