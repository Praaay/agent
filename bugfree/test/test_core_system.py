#!/usr/bin/env python3
"""
Core System Test
Comprehensive test for the Bugfree core system including orchestrator, agents, and error processing.
"""

import asyncio
import time
import sys
import os
from typing import List, Dict, Any

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bugfree.core.orchestrator import OrchestratorAgent
from bugfree.agents.log_agent import LogAgent
from bugfree.agents.code_agent import CodeAgent
from bugfree.models.error_models import ErrorContext, ErrorType, ErrorSeverity, FixSuggestion
from bugfree.models.mcp_models import MCPRequest, MCPResponse


class CoreSystemTest:
    """Comprehensive test for the core system."""
    
    def __init__(self):
        self.orchestrator = None
        self.log_agent = None
        self.code_agent = None
        self.test_results = []
        self.start_time = None
    
    def log_test_result(self, test_name: str, success: bool, details: str = "", duration: float = 0):
        """Log a test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        duration_str = f" ({duration:.2f}s)" if duration > 0 else ""
        print(f"{status} {test_name}{duration_str}")
        if details:
            print(f"   Details: {details}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "duration": duration
        })
    
    async def setup(self):
        """Set up the test environment."""
        print("🔧 Setting up core system test environment...")
        self.start_time = time.time()
        
        # Initialize agents
        self.orchestrator = OrchestratorAgent()
        self.log_agent = LogAgent()
        self.code_agent = CodeAgent()
        
        # Start agents
        print("Starting Log Agent...")
        await self.log_agent.start()
        
        print("Starting Code Agent...")
        await self.code_agent.start()
        
        print("Starting Orchestrator...")
        await self.orchestrator.start()
        
        # Wait for connections to establish
        await asyncio.sleep(3)
        
        print("✅ Core system test environment ready")
    
    async def teardown(self):
        """Clean up the test environment."""
        print("🧹 Cleaning up core system test environment...")
        
        if self.orchestrator:
            await self.orchestrator.stop()
        if self.log_agent:
            await self.log_agent.stop()
        if self.code_agent:
            await self.code_agent.stop()
        
        total_time = time.time() - self.start_time
        print(f"✅ Core system test environment cleaned up (Total time: {total_time:.2f}s)")
    
    async def test_agent_startup(self):
        """Test that all agents start up correctly."""
        print("\n🚀 Testing Agent Startup...")
        
        # Check if agents are running
        log_running = self.log_agent.running
        code_running = self.code_agent.running
        
        # Check orchestrator connections
        orchestrator_connections = len(self.orchestrator.agents)
        
        success = log_running and code_running and orchestrator_connections >= 2
        
        details = f"Log Agent: {'Running' if log_running else 'Stopped'}, " \
                 f"Code Agent: {'Running' if code_running else 'Stopped'}, " \
                 f"Orchestrator Connections: {orchestrator_connections}"
        
        self.log_test_result("Agent Startup", success, details)
    
    async def test_mcp_communication(self):
        """Test MCP communication between agents."""
        print("\n📡 Testing MCP Communication...")
        
        # Test direct MCP request from orchestrator to log agent
        try:
            test_request = MCPRequest(
                id="test_001",
                method="analyze_error",
                params={"error_context": {"error_message": "Test error"}},
                source_agent="orchestrator",
                target_agent="log_agent"
            )
            
            response = await self.orchestrator.mcp_client.send_request("log_agent", test_request)
            
            success = response is not None
            details = f"Received response: {response.result if response else 'None'}"
            
        except Exception as e:
            success = False
            details = f"Communication failed: {e}"
        
        self.log_test_result("MCP Communication", success, details)
    
    async def test_error_processing_flow(self):
        """Test the complete error processing flow."""
        print("\n🔄 Testing Error Processing Flow...")
        
        test_errors = [
            {
                "name": "NameError",
                "context": ErrorContext(
                    error_type=ErrorType.NAME_ERROR,
                    error_message="NameError: name 'undefined_var' is not defined",
                    file_path="test_name_error.py",
                    line_number=5,
                    severity=ErrorSeverity.MEDIUM,
                )
            },
            {
                "name": "TypeError",
                "context": ErrorContext(
                    error_type=ErrorType.TYPE_ERROR,
                    error_message="TypeError: 'int' object is not callable",
                    file_path="test_type_error.py",
                    line_number=10,
                    severity=ErrorSeverity.MEDIUM,
                )
            },
            {
                "name": "ImportError",
                "context": ErrorContext(
                    error_type=ErrorType.IMPORT_ERROR,
                    error_message="ModuleNotFoundError: No module named 'requests'",
                    file_path="test_import_error.py",
                    line_number=3,
                    severity=ErrorSeverity.MEDIUM,
                )
            }
        ]
        
        total_success = True
        total_suggestions = 0
        
        for error_test in test_errors:
            print(f"  Testing {error_test['name']}...")
            
            start_time = time.time()
            suggestions = await self.orchestrator.process_error(error_test['context'])
            duration = time.time() - start_time
            
            success = len(suggestions) > 0
            total_success = total_success and success
            total_suggestions += len(suggestions)
            
            details = f"{error_test['name']}: {len(suggestions)} suggestions in {duration:.2f}s"
            self.log_test_result(f"Error Processing - {error_test['name']}", success, details, duration)
        
        # Overall flow test
        overall_success = total_success and total_suggestions > 0
        overall_details = f"Total suggestions generated: {total_suggestions}"
        self.log_test_result("Complete Error Processing Flow", overall_success, overall_details)
    
    async def test_suggestion_ranking(self):
        """Test suggestion ranking and filtering."""
        print("\n📊 Testing Suggestion Ranking...")
        
        # Create test suggestions with different confidence scores
        test_suggestions = [
            FixSuggestion(
                title="High Confidence Fix",
                description="This should rank high",
                code_snippet="fix_high = True",
                confidence_score=0.9,
                agent_source="code_agent",
                explanation="High confidence explanation"
            ),
            FixSuggestion(
                title="Medium Confidence Fix",
                description="This should rank medium",
                code_snippet="fix_medium = True",
                confidence_score=0.6,
                agent_source="log_agent",
                explanation="Medium confidence explanation"
            ),
            FixSuggestion(
                title="Low Confidence Fix",
                description="This should rank low",
                code_snippet="fix_low = True",
                confidence_score=0.3,
                agent_source="code_agent",
                explanation="Low confidence explanation"
            )
        ]
        
        # Test ranking
        error_context = ErrorContext(
            error_type=ErrorType.NAME_ERROR,
            error_message="Test error",
            file_path="test.py",
            line_number=1,
            severity=ErrorSeverity.MEDIUM,
        )
        
        ranked_suggestions = await self.orchestrator._rank_suggestions(test_suggestions, error_context)
        
        # Check that suggestions are ranked by confidence (highest first)
        success = len(ranked_suggestions) > 0
        if success and len(ranked_suggestions) >= 2:
            first_score = ranked_suggestions[0].confidence_score
            second_score = ranked_suggestions[1].confidence_score
            success = first_score >= second_score
        
        details = f"Ranked {len(ranked_suggestions)} suggestions, top confidence: {ranked_suggestions[0].confidence_score if ranked_suggestions else 'N/A'}"
        self.log_test_result("Suggestion Ranking", success, details)
    
    async def test_session_management(self):
        """Test debug session management."""
        print("\n📋 Testing Session Management...")
        
        # Create a test error to generate a session
        test_error = ErrorContext(
            error_type=ErrorType.NAME_ERROR,
            error_message="Session test error",
            file_path="session_test.py",
            line_number=1,
            severity=ErrorSeverity.MEDIUM,
        )
        
        await self.orchestrator.process_error(test_error)
        
        # Check session creation
        active_sessions = self.orchestrator.get_active_sessions()
        session_created = len(active_sessions) > 0
        
        if session_created:
            session = active_sessions[0]
            session_has_errors = len(session.errors) > 0
            session_has_suggestions = len(session.applied_fixes) > 0
            
            success = session_created and session_has_errors
            details = f"Session created with {len(session.errors)} errors and {len(session.applied_fixes)} suggestions"
        else:
            success = False
            details = "No session created"
        
        self.log_test_result("Session Management", success, details)
    
    async def test_agent_health_check(self):
        """Test agent health monitoring."""
        print("\n💓 Testing Agent Health Check...")
        
        # Check orchestrator agent status
        orchestrator_healthy = self.orchestrator.agents.get("log_agent", {}).get("connected", False) and \
                              self.orchestrator.agents.get("code_agent", {}).get("connected", False)
        
        # Check individual agent status
        log_healthy = self.log_agent.running
        code_healthy = self.code_agent.running
        
        success = orchestrator_healthy and log_healthy and code_healthy
        
        details = f"Orchestrator connections: {orchestrator_healthy}, " \
                 f"Log Agent: {log_healthy}, Code Agent: {code_healthy}"
        
        self.log_test_result("Agent Health Check", success, details)
    
    async def test_error_type_detection(self):
        """Test error type detection and matching."""
        print("\n🔍 Testing Error Type Detection...")
        
        error_types_to_test = [
            (ErrorType.NAME_ERROR, "NameError: name 'x' is not defined"),
            (ErrorType.TYPE_ERROR, "TypeError: 'int' object is not callable"),
            (ErrorType.IMPORT_ERROR, "ModuleNotFoundError: No module named 'requests'"),
            (ErrorType.ATTRIBUTE_ERROR, "AttributeError: 'str' object has no attribute 'append'"),
            (ErrorType.INDEX_ERROR, "IndexError: list index out of range"),
            (ErrorType.KEY_ERROR, "KeyError: 'missing_key'"),
        ]
        
        success_count = 0
        
        for expected_type, error_message in error_types_to_test:
            error_context = ErrorContext(
                error_type=expected_type,
                error_message=error_message,
                file_path="test.py",
                line_number=1,
                severity=ErrorSeverity.MEDIUM,
            )
            
            # Test suggestion matching
            test_suggestion = FixSuggestion(
                title=f"Fix for {expected_type.value}",
                description="Test suggestion",
                code_snippet="test_fix()",
                confidence_score=0.8,
                agent_source="code_agent",
            )
            
            matches = self.orchestrator._suggestion_matches_error_type(test_suggestion, error_context)
            if matches:
                success_count += 1
        
        success = success_count > 0
        details = f"Matched {success_count}/{len(error_types_to_test)} error types"
        
        self.log_test_result("Error Type Detection", success, details)
    
    async def test_performance_benchmark(self):
        """Test system performance with multiple concurrent errors."""
        print("\n⚡ Testing Performance Benchmark...")
        
        # Create multiple concurrent error processing tasks
        test_errors = []
        for i in range(5):
            error_context = ErrorContext(
                error_type=ErrorType.NAME_ERROR,
                error_message=f"Concurrent error {i}",
                file_path=f"test_concurrent_{i}.py",
                line_number=i + 1,
                severity=ErrorSeverity.MEDIUM,
            )
            test_errors.append(error_context)
        
        # Process errors concurrently
        start_time = time.time()
        tasks = [self.orchestrator.process_error(error) for error in test_errors]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Check results
        successful_results = [r for r in results if isinstance(r, list) and len(r) > 0]
        success = len(successful_results) >= 3  # At least 3 should succeed
        
        total_suggestions = sum(len(r) for r in successful_results)
        avg_time_per_error = total_time / len(test_errors)
        
        details = f"Processed {len(test_errors)} errors in {total_time:.2f}s " \
                 f"({avg_time_per_error:.2f}s avg), {len(successful_results)} successful, " \
                 f"{total_suggestions} total suggestions"
        
        self.log_test_result("Performance Benchmark", success, details, total_time)
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*60)
        print("📊 CORE SYSTEM TEST SUMMARY")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        
        if total_tests > 0:
            print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        else:
            print("Success Rate: N/A (no tests completed)")
        
        if failed_tests > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['details']}")
        
        total_time = time.time() - self.start_time
        print(f"\n⏱️  Total Test Time: {total_time:.2f}s")
        
        if total_tests > 0 and passed_tests == total_tests:
            print("\n🎉 ALL TESTS PASSED! Core system is working correctly.")
        elif total_tests > 0:
            print(f"\n⚠️  {failed_tests} test(s) failed. Please check the details above.")
        else:
            print("\n⚠️  No tests were completed due to setup errors.")
    
    async def run_all_tests(self):
        """Run all core system tests."""
        print("🧪 Starting Core System Tests...")
        print("="*60)
        
        try:
            await self.setup()
            
            # Run all tests
            await self.test_agent_startup()
            await self.test_mcp_communication()
            await self.test_error_processing_flow()
            await self.test_suggestion_ranking()
            await self.test_session_management()
            await self.test_agent_health_check()
            await self.test_error_type_detection()
            await self.test_performance_benchmark()
            
        except Exception as e:
            print(f"❌ Test execution failed: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await self.teardown()
            self.print_summary()


async def main():
    """Main test runner."""
    test = CoreSystemTest()
    await test.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main()) 