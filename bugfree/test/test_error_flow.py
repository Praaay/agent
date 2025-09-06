#!/usr/bin/env python3
"""
Test script for error processing flow
Tests the complete end-to-end error processing from detection to fix suggestions.
"""

import asyncio
import time
import sys
import os
from typing import List

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bugfree.core.orchestrator import OrchestratorAgent
from bugfree.agents.log_agent import LogAgent
from bugfree.agents.code_agent import CodeAgent
from bugfree.models.error_models import ErrorContext, ErrorType, ErrorSeverity


class ErrorFlowTest:
    """Test the complete error processing flow."""
    
    def __init__(self):
        self.orchestrator = None
        self.log_agent = None
        self.code_agent = None
    
    async def setup(self):
        """Set up the test environment."""
        print("🔧 Setting up error flow test environment...")
        
        # Initialize agents
        self.orchestrator = OrchestratorAgent()
        self.log_agent = LogAgent()
        self.code_agent = CodeAgent()
        
        # Start agents
        await self.log_agent.start()
        await self.code_agent.start()
        await self.orchestrator.start()
        
        # Wait for connections to establish
        await asyncio.sleep(2)
        
        print("✅ Error flow test environment ready")
    
    async def teardown(self):
        """Clean up the test environment."""
        print("🧹 Cleaning up error flow test environment...")
        
        if self.orchestrator:
            await self.orchestrator.stop()
        if self.log_agent:
            await self.log_agent.stop()
        if self.code_agent:
            await self.code_agent.stop()
        
        print("✅ Error flow test environment cleaned up")
    
    async def test_name_error_flow(self):
        """Test processing of a NameError."""
        print("\n🧪 Testing NameError Processing Flow...")
        
        # Create a NameError
        name_error = ErrorContext(
            error_type=ErrorType.NAME_ERROR,
            error_message="NameError: name 'undefined_var' is not defined",
            file_path="test_name_error.py",
            line_number=5,
            severity=ErrorSeverity.MEDIUM,
        )
        
        print(f"Processing error: {name_error.error_message}")
        
        # Process through orchestrator
        start_time = time.time()
        suggestions = await self.orchestrator.process_error(name_error)
        processing_time = time.time() - start_time
        
        print(f"Processing completed in {processing_time:.2f}s")
        print(f"Received {len(suggestions)} suggestions:")
        
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion.title}")
            print(f"     Description: {suggestion.description}")
            print(f"     Confidence: {suggestion.confidence_score}")
            print(f"     Agent: {suggestion.agent_source}")
            print(f"     Code: {suggestion.code_snippet}")
            print()
        
        # Validate results
        success = len(suggestions) > 0 and processing_time < 5.0
        
        if success:
            print("✅ NameError processing flow test PASSED")
        else:
            print("❌ NameError processing flow test FAILED")
        
        return success
    
    async def test_import_error_flow(self):
        """Test processing of an ImportError."""
        print("\n🧪 Testing ImportError Processing Flow...")
        
        # Create an ImportError
        import_error = ErrorContext(
            error_type=ErrorType.IMPORT_ERROR,
            error_message="ModuleNotFoundError: No module named 'nonexistent_module'",
            file_path="test_import_error.py",
            line_number=3,
            severity=ErrorSeverity.MEDIUM,
        )
        
        print(f"Processing error: {import_error.error_message}")
        
        # Process through orchestrator
        start_time = time.time()
        suggestions = await self.orchestrator.process_error(import_error)
        processing_time = time.time() - start_time
        
        print(f"Processing completed in {processing_time:.2f}s")
        print(f"Received {len(suggestions)} suggestions:")
        
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion.title}")
            print(f"     Description: {suggestion.description}")
            print(f"     Confidence: {suggestion.confidence_score}")
            print(f"     Agent: {suggestion.agent_source}")
            print(f"     Code: {suggestion.code_snippet}")
            print()
        
        # Validate results
        success = len(suggestions) > 0 and processing_time < 5.0
        
        if success:
            print("✅ ImportError processing flow test PASSED")
        else:
            print("❌ ImportError processing flow test FAILED")
        
        return success
    
    async def test_attribute_error_flow(self):
        """Test processing of an AttributeError."""
        print("\n🧪 Testing AttributeError Processing Flow...")
        
        # Create an AttributeError
        attribute_error = ErrorContext(
            error_type=ErrorType.ATTRIBUTE_ERROR,
            error_message="AttributeError: 'list' object has no attribute 'append_item'",
            file_path="test_attribute_error.py",
            line_number=7,
            severity=ErrorSeverity.MEDIUM,
        )
        
        print(f"Processing error: {attribute_error.error_message}")
        
        # Process through orchestrator
        start_time = time.time()
        suggestions = await self.orchestrator.process_error(attribute_error)
        processing_time = time.time() - start_time
        
        print(f"Processing completed in {processing_time:.2f}s")
        print(f"Received {len(suggestions)} suggestions:")
        
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion.title}")
            print(f"     Description: {suggestion.description}")
            print(f"     Confidence: {suggestion.confidence_score}")
            print(f"     Agent: {suggestion.agent_source}")
            print(f"     Code: {suggestion.code_snippet}")
            print()
        
        # Validate results
        success = len(suggestions) > 0 and processing_time < 5.0
        
        if success:
            print("✅ AttributeError processing flow test PASSED")
        else:
            print("❌ AttributeError processing flow test FAILED")
        
        return success
    
    async def test_multiple_errors_flow(self):
        """Test processing multiple errors in sequence."""
        print("\n🧪 Testing Multiple Errors Processing Flow...")
        
        # Create multiple errors
        errors = [
            ErrorContext(
                error_type=ErrorType.NAME_ERROR,
                error_message="NameError: name 'var1' is not defined",
                file_path="test_multiple.py",
                line_number=1,
                severity=ErrorSeverity.MEDIUM,
            ),
            ErrorContext(
                error_type=ErrorType.INDEX_ERROR,
                error_message="IndexError: list index out of range",
                file_path="test_multiple.py",
                line_number=10,
                severity=ErrorSeverity.MEDIUM,
            ),
            ErrorContext(
                error_type=ErrorType.KEY_ERROR,
                error_message="KeyError: 'missing_key'",
                file_path="test_multiple.py",
                line_number=15,
                severity=ErrorSeverity.MEDIUM,
            ),
        ]
        
        all_success = True
        
        for i, error in enumerate(errors, 1):
            print(f"\nProcessing error {i}: {error.error_message}")
            
            start_time = time.time()
            suggestions = await self.orchestrator.process_error(error)
            processing_time = time.time() - start_time
            
            print(f"  Processing time: {processing_time:.2f}s")
            print(f"  Suggestions: {len(suggestions)}")
            
            success = len(suggestions) > 0 and processing_time < 5.0
            if not success:
                all_success = False
        
        if all_success:
            print("✅ Multiple errors processing flow test PASSED")
        else:
            print("❌ Multiple errors processing flow test FAILED")
        
        return all_success
    
    async def test_suggestion_ranking_flow(self):
        """Test that suggestions are properly ranked."""
        print("\n🧪 Testing Suggestion Ranking Flow...")
        
        # Create an error that should generate multiple suggestions
        error = ErrorContext(
            error_type=ErrorType.NAME_ERROR,
            error_message="NameError: name 'complex_var' is not defined",
            file_path="test_ranking.py",
            line_number=1,
            severity=ErrorSeverity.MEDIUM,
        )
        
        print(f"Processing error: {error.error_message}")
        
        # Process through orchestrator
        suggestions = await self.orchestrator.process_error(error)
        
        if len(suggestions) < 2:
            print("❌ Not enough suggestions to test ranking")
            return False
        
        print(f"Received {len(suggestions)} suggestions:")
        
        # Check if suggestions are ranked by confidence
        for i, suggestion in enumerate(suggestions):
            print(f"  {i+1}. {suggestion.title} (confidence: {suggestion.confidence_score})")
        
        # Validate ranking (should be in descending order of confidence)
        is_ranked = all(
            suggestions[i].confidence_score >= suggestions[i+1].confidence_score
            for i in range(len(suggestions) - 1)
        )
        
        if is_ranked:
            print("✅ Suggestion ranking flow test PASSED")
        else:
            print("❌ Suggestion ranking flow test FAILED")
        
        return is_ranked
    
    async def run_all_tests(self):
        """Run all error flow tests."""
        print("🚀 Starting Error Processing Flow Tests")
        print("=" * 60)
        
        test_results = []
        
        try:
            await self.setup()
            
            # Run all tests
            tests = [
                ("NameError Flow", self.test_name_error_flow),
                ("ImportError Flow", self.test_import_error_flow),
                ("AttributeError Flow", self.test_attribute_error_flow),
                ("Multiple Errors Flow", self.test_multiple_errors_flow),
                ("Suggestion Ranking Flow", self.test_suggestion_ranking_flow),
            ]
            
            for test_name, test_func in tests:
                try:
                    result = await test_func()
                    test_results.append((test_name, result))
                except Exception as e:
                    print(f"❌ {test_name} failed with exception: {e}")
                    test_results.append((test_name, False))
            
        finally:
            await self.teardown()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📋 Error Flow Test Summary")
        print("=" * 60)
        
        passed = sum(1 for _, result in test_results if result)
        total = len(test_results)
        
        for test_name, result in test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All error flow tests passed! The system is working correctly.")
            return True
        else:
            print("⚠️ Some error flow tests failed. Check the details above.")
            return False


async def main():
    """Main test runner."""
    error_flow_test = ErrorFlowTest()
    success = await error_flow_test.run_all_tests()
    
    if success:
        print("\n✅ Error flow tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Error flow tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 