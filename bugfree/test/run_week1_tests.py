#!/usr/bin/env python3
"""
Week 1 Test Runner
Runs all Week 1 tests for the Bugfree Multi-Agent Debugging System.
"""

import asyncio
import sys
import os
import time
from typing import List, Dict, Any

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
 
# Import test modules
from test_network import NetworkTestSuite
from test_error_flow import ErrorFlowTest
from test_connectivity import ConnectivityTest


class Week1TestRunner:
    """Comprehensive test runner for Week 1 implementation."""
    
    def __init__(self):
        self.test_results = []
        self.start_time = None
    
    def log_test_suite_result(self, suite_name: str, success: bool, details: str = ""):
        """Log a test suite result."""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {suite_name}")
        if details:
            print(f"   Details: {details}")
        
        self.test_results.append({
            "suite": suite_name,
            "success": success,
            "details": details
        })
    
    async def run_network_tests(self):
        """Run network layer tests."""
        print("\n" + "=" * 80)
        print("🌐 RUNNING NETWORK LAYER TESTS")
        print("=" * 80)
        
        try:
            test_suite = NetworkTestSuite()
            success = await test_suite.run_all_tests()
            
            self.log_test_suite_result(
                "Network Layer Tests",
                success,
                f"Network connectivity and communication tests"
            )
            
            return success
            
        except Exception as e:
            self.log_test_suite_result("Network Layer Tests", False, str(e))
            return False
    
    async def run_error_flow_tests(self):
        """Run error processing flow tests."""
        print("\n" + "=" * 80)
        print("🔄 RUNNING ERROR PROCESSING FLOW TESTS")
        print("=" * 80)
        
        try:
            test_suite = ErrorFlowTest()
            success = await test_suite.run_all_tests()
            
            self.log_test_suite_result(
                "Error Processing Flow Tests",
                success,
                f"End-to-end error processing and suggestion generation tests"
            )
            
            return success
            
        except Exception as e:
            self.log_test_suite_result("Error Processing Flow Tests", False, str(e))
            return False
    
    async def run_connectivity_tests(self):
        """Run connectivity validation tests."""
        print("\n" + "=" * 80)
        print("🔗 RUNNING CONNECTIVITY VALIDATION TESTS")
        print("=" * 80)
        
        try:
            test_suite = ConnectivityTest()
            success = await test_suite.run_all_tests()
            
            self.log_test_suite_result(
                "Connectivity Validation Tests",
                success,
                f"Network connectivity and stability tests"
            )
            
            return success
            
        except Exception as e:
            self.log_test_suite_result("Connectivity Validation Tests", False, str(e))
            return False
    
    async def run_quick_smoke_test(self):
        """Run a quick smoke test to verify basic functionality."""
        print("\n" + "=" * 80)
        print("💨 RUNNING QUICK SMOKE TEST")
        print("=" * 80)
        
        try:
            # Import required modules
            from bugfree.core.orchestrator import OrchestratorAgent
            from bugfree.agents.log_agent import LogAgent
            from bugfree.agents.code_agent import CodeAgent
            from bugfree.models.error_models import ErrorContext, ErrorType, ErrorSeverity
            
            # Initialize agents
            orchestrator = OrchestratorAgent()
            log_agent = LogAgent()
            code_agent = CodeAgent()
            
            # Start agents
            await log_agent.start()
            await code_agent.start()
            await orchestrator.start()
            
            # Wait for connections
            await asyncio.sleep(2)
            
            # Test basic error processing
            test_error = ErrorContext(
                error_type=ErrorType.NAME_ERROR,
                error_message="NameError: name 'test_var' is not defined",
                file_path="test.py",
                line_number=1,
                severity=ErrorSeverity.MEDIUM,
            )
            
            suggestions = await orchestrator.process_error(test_error)
            
            # Clean up
            await orchestrator.stop()
            await log_agent.stop()
            await code_agent.stop()
            
            success = len(suggestions) > 0
            
            self.log_test_suite_result(
                "Quick Smoke Test",
                success,
                f"Basic functionality test - {len(suggestions)} suggestions generated"
            )
            
            return success
            
        except Exception as e:
            self.log_test_suite_result("Quick Smoke Test", False, str(e))
            return False
    
    def print_week1_summary(self):
        """Print a summary of Week 1 implementation."""
        print("\n" + "=" * 80)
        print("📋 WEEK 1 IMPLEMENTATION SUMMARY")
        print("=" * 80)
        
        print("✅ COMPLETED TASKS:")
        print("   • Network Layer Fixes")
        print("     - Added retry logic and timeout handling")
        print("     - Improved error handling for network failures")
        print("     - Added connection health checking")
        print("     - Implemented graceful connection recovery")
        
        print("\n   • Agent Handler Completion")
        print("     - Completed Log Agent error analysis handlers")
        print("     - Completed Code Agent fix suggestion handlers")
        print("     - Completed Orchestrator coordination handlers")
        print("     - Added comprehensive error pattern recognition")
        
        print("\n   • Testing Infrastructure")
        print("     - Created comprehensive test suite for agent communication")
        print("     - Implemented error processing flow tests")
        print("     - Added network connectivity validation")
        print("     - Created smoke tests for basic functionality")
        
        print("\n🔧 TECHNICAL IMPROVEMENTS:")
        print("   • Enhanced MCPClient with timeout and retry logic")
        print("   • Improved MCPServer with better error handling")
        print("   • Added comprehensive error pattern matching")
        print("   • Implemented intelligent suggestion ranking")
        print("   • Added connection health monitoring")
        print("   • Created robust test infrastructure")
        
        print("\n📊 TEST COVERAGE:")
        print("   • Network connectivity and communication")
        print("   • Error processing and suggestion generation")
        print("   • Agent coordination and ranking")
        print("   • Timeout handling and error recovery")
        print("   • Concurrent connection handling")
    
    async def run_all_tests(self):
        """Run all Week 1 tests."""
        print("🚀 STARTING WEEK 1 COMPREHENSIVE TEST SUITE")
        print("=" * 80)
        print("Testing Week 1 Implementation: Core Infrastructure")
        print("=" * 80)
        
        self.start_time = time.time()
        
        # Run all test suites
        test_suites = [
            ("Quick Smoke Test", self.run_quick_smoke_test),
            ("Network Layer Tests", self.run_network_tests),
            ("Error Processing Flow Tests", self.run_error_flow_tests),
            ("Connectivity Validation Tests", self.run_connectivity_tests),
        ]
        
        for suite_name, test_func in test_suites:
            try:
                await test_func()
            except Exception as e:
                self.log_test_suite_result(suite_name, False, f"Test suite failed with exception: {e}")
        
        # Calculate total time
        total_time = time.time() - self.start_time
        
        # Print final summary
        print("\n" + "=" * 80)
        print("📊 WEEK 1 TEST RESULTS SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        for result in self.test_results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"{status} {result['suite']}")
            if result["details"]:
                print(f"   {result['details']}")
        
        print(f"\nOverall: {passed}/{total} test suites passed")
        print(f"Total execution time: {total_time:.2f} seconds")
        
        # Print implementation summary
        self.print_week1_summary()
        
        if passed == total:
            print("\n🎉 WEEK 1 IMPLEMENTATION COMPLETE!")
            print("✅ All tests passed! The core infrastructure is working correctly.")
            print("\n📈 READY FOR WEEK 2:")
            print("   • Log Agent Enhancement")
            print("   • Real-time log monitoring")
            print("   • Stack trace parsing")
            print("   • Error pattern recognition")
            return True
        else:
            print("\n⚠️ WEEK 1 IMPLEMENTATION INCOMPLETE")
            print("❌ Some tests failed. Please fix the issues before proceeding to Week 2.")
            return False


async def main():
    """Main test runner."""
    test_runner = Week1TestRunner()
    success = await test_runner.run_all_tests()
    
    if success:
        print("\n✅ Week 1 tests completed successfully!")
        print("🚀 Ready to proceed with Week 2 implementation!")
        sys.exit(0)
    else:
        print("\n❌ Week 1 tests failed!")
        print("🔧 Please fix the failing tests before proceeding.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 