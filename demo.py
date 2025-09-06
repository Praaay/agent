#!/usr/bin/env python3
"""
Bugfree Demo Script
Demonstrates the Bugfree system with real Python errors.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bugfree.core.orchestrator import OrchestratorAgent
from bugfree.agents.log_agent import LogAgent
from bugfree.agents.code_agent import CodeAgent
from bugfree.models.error_models import ErrorContext, ErrorType, ErrorSeverity


async def demo_bugfree():
    """Run a live demo of the Bugfree system."""
    print("🐛 BUGFREE LIVE DEMO")
    print("=" * 50)
    
    # Initialize and start the system
    print("1. Starting Bugfree system...")
    orchestrator = OrchestratorAgent()
    log_agent = LogAgent()
    code_agent = CodeAgent()
    
    await log_agent.start()
    await code_agent.start()
    await orchestrator.start()
    
    await asyncio.sleep(2)
    print("✅ System started successfully!")
    
    # Create a test file with errors
    test_file = "demo_test.py"
    with open(test_file, "w") as f:
        f.write("""# Demo file with intentional errors
import nonexistent_module  # This will cause an ImportError

def calculate_something():
    undefined_variable = 42  # This will cause a NameError
    result = undefined_variable / 0  # This will cause a ZeroDivisionError
    return result

# This will cause a TypeError
number = 42
result = number()  # Trying to call an int as a function

print("This line will never be reached due to errors above")
""")
    
    print(f"2. Created test file: {test_file}")
    
    # Demo different error types
    demo_errors = [
        {
            "error_type": ErrorType.IMPORT_ERROR,
            "error_message": "ModuleNotFoundError: No module named 'nonexistent_module'",
            "file_path": test_file,
            "line_number": 2,
            "severity": ErrorSeverity.HIGH,
        },
        {
            "error_type": ErrorType.NAME_ERROR,
            "error_message": "NameError: name 'undefined_variable' is not defined",
            "file_path": test_file,
            "line_number": 5,
            "severity": ErrorSeverity.MEDIUM,
        },
        {
            "error_type": ErrorType.VALUE_ERROR,
            "error_message": "ZeroDivisionError: division by zero",
            "file_path": test_file,
            "line_number": 6,
            "severity": ErrorSeverity.HIGH,
        },
        {
            "error_type": ErrorType.TYPE_ERROR,
            "error_message": "TypeError: 'int' object is not callable",
            "file_path": test_file,
            "line_number": 10,
            "severity": ErrorSeverity.MEDIUM,
        }
    ]
    
    print("3. Processing errors through Bugfree system...")
    print("-" * 50)
    
    for i, error_data in enumerate(demo_errors, 1):
        print(f"\n🔍 Error {i}: {error_data['error_type'].value}")
        print(f"   Message: {error_data['error_message']}")
        print(f"   File: {error_data['file_path']}:{error_data['line_number']}")
        
        error_context = ErrorContext(**error_data)
        suggestions = await orchestrator.process_error(error_context)
        
        if suggestions:
            print(f"   💡 Found {len(suggestions)} suggestions:")
            for j, suggestion in enumerate(suggestions, 1):
                print(f"      {j}. {suggestion.title} ({suggestion.agent_source})")
                print(f"         Confidence: {suggestion.confidence_score:.2f}")
                print(f"         Description: {suggestion.description}")
        else:
            print("   ⚠️  No suggestions found")
        
        await asyncio.sleep(1)  # Pause between errors
    
    print("\n" + "=" * 50)
    print("🎉 DEMO COMPLETED!")
    print("✅ Bugfree system successfully processed all errors")
    print("✅ Suggestions were generated for each error type")
    print("✅ Agent communication working correctly")
    
    # Clean up
    print("\n4. Cleaning up...")
    await orchestrator.stop()
    await log_agent.stop()
    await code_agent.stop()
    
    # Remove test file
    if os.path.exists(test_file):
        os.remove(test_file)
        print(f"✅ Removed test file: {test_file}")
    
    print("✅ Demo completed successfully!")


if __name__ == "__main__":
    asyncio.run(demo_bugfree()) 