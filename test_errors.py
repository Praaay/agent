#!/usr/bin/env python3
"""
Test file with intentional errors to demonstrate Bugfree system
"""

# This will cause a NameError
print(undefined_variable)

# This will cause a TypeError
result = "hello" + 42

# This will cause an ImportError
import nonexistent_module

# This will cause a ZeroDivisionError
result = 10 / 0

print("This line should never be reached") 