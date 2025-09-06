#!/usr/bin/env python3
"""
Test script that connects to the running Bugfree system.
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bugfree.core.orchestrator import OrchestratorAgent
from bugfree.models.error_models import ErrorContext, ErrorType, ErrorSeverity


async def test_live_system():
    """Test the running Bugfree system."""
    print("🧪 Testing Live Bugfree System")
    print("=" * 40)
    
    # Create orchestrator that connects to running agents
    orchestrator = OrchestratorAgent()
    
    try:
        # Connect to running agents
        print("1. Connecting to running agents...")
        await orchestrator.start()
        
        # Wait for connections
        await asyncio.sleep(2)
        
        # Test error analysis
        print("2. Testing error analysis...")
        error_context = ErrorContext(
            error_type=ErrorType.IMPORT_ERROR,
            error_message="ModuleNotFoundError: No module named 'nonexistent_module'",
            file_path="test_error.py",
            line_number=7,
            severity=ErrorSeverity.HIGH,
        )
        
        suggestions = await orchestrator.process_error(error_context)
        
        print(f"3. Results: Found {len(suggestions)} suggestions")
        
        for i, suggestion in enumerate(suggestions, 1):
            print(f"\n💡 Suggestion {i}:")
            print(f"   Title: {suggestion.title}")
            print(f"   Agent: {suggestion.agent_source}")
            print(f"   Confidence: {suggestion.confidence_score:.2f}")
            print(f"   Description: {suggestion.description}")
            if suggestion.code_snippet:
                print(f"   Code: {suggestion.code_snippet}")
        
        print("\n✅ Live system test completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await orchestrator.stop()


if __name__ == "__main__":
    asyncio.run(test_live_system()) 