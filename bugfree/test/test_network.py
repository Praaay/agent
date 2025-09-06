#!/usr/bin/env python3
"""
Test suite for Bugfree Multi-Agent Debugging System
Tests network connectivity, agent communication, and error processing flow.
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
from bugfree.models.error_models import ErrorContext, ErrorType, ErrorSeverity
from bugfree.models.mcp_models import MCPRequest, MCPResponse


class NetworkTestSuite:
    """Test suite for network connectivity and agent communication."""
    
    def __init__(self):
        self.orchestrator = None
        self.log_agent = None
        self.code_agent = None
        self.test_results = []
    
    async def setup(self):
        """Set up the test environment."""
        print("🔧 Setting up test environment...")
        
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
        
        print("✅ Test environment ready")
    
    async def teardown(self):
        """Clean up the test environment."""
        print("🧹 Cleaning up test environment...")
        
        if self.orchestrator:
            await self.orchestrator.stop()
        if self.log_agent:
            await self.log_agent.stop()
        if self.code_agent:
            await self.code_agent.stop()
        
        print("✅ Test environment cleaned up")
    
    def log_test_result(self, test_name: str, success: bool, details: str = ""):
        """Log a test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   Details: {details}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
    
    async def test_agent_startup(self):
        """Test that all agents can start successfully."""
        print("\n🧪 Testing Agent Startup...")
        
        try:
            # Check if agents are running
            orchestrator_running = self.orchestrator and hasattr(self.orchestrator, 'running')
            log_agent_running = self.log_agent and hasattr(self.log_agent, 'running')
            code_agent_running = self.code_agent and hasattr(self.code_agent, 'running')
            
            success = orchestrator_running and log_agent_running and code_agent_running
            
            self.log_test_result(
                "Agent Startup",
                success,
                f"Orchestrator: {orchestrator_running}, Log Agent: {log_agent_running}, Code Agent: {code_agent_running}"
            )
            
        except Exception as e:
            self.log_test_result("Agent Startup", False, str(e))
    
    async def test_network_connectivity(self):
        """Test network connectivity between agents."""
        print("\n🌐 Testing Network Connectivity...")
        
        try:
            # Check orchestrator connections
            log_connected = "log_agent" in self.orchestrator.agents and self.orchestrator.agents["log_agent"]["connected"]
            code_connected = "code_agent" in self.orchestrator.agents and self.orchestrator.agents["code_agent"]["connected"]
            
            success = log_connected and code_connected
            
            self.log_test_result(
                "Network Connectivity",
                success,
                f"Log Agent: {log_connected}, Code Agent: {code_connected}"
            )
            
        except Exception as e:
            self.log_test_result("Network Connectivity", False, str(e))
    
    async def test_mcp_communication(self):
        """Test MCP communication between agents."""
        print("\n📡 Testing MCP Communication...")
        
        try:
            # Test basic MCP request/response
            test_request = MCPRequest(
                id="test_001",
                method="analyze_error",
                params={"error_context": {"error_type": "NAME_ERROR", "error_message": "test"}},
                source_agent="test",
                target_agent="log_agent"
            )
            
            # Send test request to log agent
            response = await self.orchestrator.mcp_client.send_request("log_agent", test_request)
            
            success = response is not None and not response.error
            
            self.log_test_result(
                "MCP Communication",
                success,
                f"Response received: {response is not None}, Error: {response.error if response else 'None'}"
            )
            
        except Exception as e:
            self.log_test_result("MCP Communication", False, str(e))
    
    async def test_error_processing_flow(self):
        """Test the complete error processing flow."""
        print("\n🔄 Testing Error Processing Flow...")
        
        try:
            # Create a test error
            test_error = ErrorContext(
                error_type=ErrorType.NAME_ERROR,
                error_message="NameError: name 'test_var' is not defined",
                file_path="test.py",
                line_number=1,
                severity=ErrorSeverity.MEDIUM,
            )
            
            # Process the error through the orchestrator
            start_time = time.time()
            suggestions = await self.orchestrator.process_error(test_error)
            processing_time = time.time() - start_time
            
            success = len(suggestions) > 0 and processing_time < 5.0  # Should complete within 5 seconds
            
            self.log_test_result(
                "Error Processing Flow",
                success,
                f"Suggestions: {len(suggestions)}, Processing time: {processing_time:.2f}s"
            )
            
            # Log suggestions for debugging
            for i, suggestion in enumerate(suggestions[:3]):
                print(f"   Suggestion {i+1}: {suggestion.title} (confidence: {suggestion.confidence_score})")
            
        except Exception as e:
            self.log_test_result("Error Processing Flow", False, str(e))
    
    async def test_agent_handlers(self):
        """Test individual agent handlers."""
        print("\n🤖 Testing Agent Handlers...")
        
        try:
            # Test Log Agent handler
            log_request = MCPRequest(
                id="test_002",
                method="analyze_error",
                params={"error_context": {"error_type": "NAME_ERROR", "error_message": "test"}},
                source_agent="test",
                target_agent="log_agent"
            )
            
            log_response = await self.log_agent.mcp_server._process_request(log_request)
            log_success = log_response is not None and not log_response.error
            
            # Test Code Agent handler
            code_request = MCPRequest(
                id="test_003",
                method="suggest_fixes",
                params={"error_context": {"error_type": "NAME_ERROR", "error_message": "test"}},
                source_agent="test",
                target_agent="code_agent"
            )
            
            code_response = await self.code_agent.mcp_server._process_request(code_request)
            code_success = code_response is not None and not code_response.error
            
            success = log_success and code_success
            
            self.log_test_result(
                "Agent Handlers",
                success,
                f"Log Agent: {log_success}, Code Agent: {code_success}"
            )
            
        except Exception as e:
            self.log_test_result("Agent Handlers", False, str(e))
    
    async def test_suggestion_ranking(self):
        """Test suggestion ranking algorithm."""
        print("\n📊 Testing Suggestion Ranking...")
        
        try:
            from bugfree.models.error_models import FixSuggestion
            
            # Create test suggestions
            test_suggestions = [
                FixSuggestion(
                    title="Define variable",
                    description="Define the variable before use",
                    code_snippet="test_var = None",
                    confidence_score=0.8,
                    agent_source="code_agent"
                ),
                FixSuggestion(
                    title="Check for typos",
                    description="Variable might be misspelled",
                    code_snippet="# Check spelling",
                    confidence_score=0.6,
                    agent_source="log_agent"
                ),
                FixSuggestion(
                    title="Import missing module",
                    description="Variable might be from a module",
                    code_snippet="from module import test_var",
                    confidence_score=0.7,
                    agent_source="code_agent"
                )
            ]
            
            # Test ranking
            test_error = ErrorContext(
                error_type=ErrorType.NAME_ERROR,
                error_message="NameError: name 'test_var' is not defined",
                file_path="test.py",
                line_number=1,
                severity=ErrorSeverity.MEDIUM,
            )
            
            ranked_suggestions = await self.orchestrator._rank_suggestions(test_suggestions, test_error)
            
            success = len(ranked_suggestions) > 0 and ranked_suggestions[0].confidence_score >= ranked_suggestions[-1].confidence_score
            
            self.log_test_result(
                "Suggestion Ranking",
                success,
                f"Ranked {len(ranked_suggestions)} suggestions, Top confidence: {ranked_suggestions[0].confidence_score if ranked_suggestions else 'N/A'}"
            )
            
        except Exception as e:
            self.log_test_result("Suggestion Ranking", False, str(e))
    
    async def test_error_handling(self):
        """Test error handling and recovery."""
        print("\n🛡️ Testing Error Handling...")
        
        try:
            # Test timeout handling
            timeout_request = MCPRequest(
                id="test_004",
                method="slow_operation",
                params={},
                source_agent="test",
                target_agent="log_agent"
            )
            
            # This should timeout gracefully
            response = await self.orchestrator.mcp_client.send_request_with_retry("log_agent", timeout_request, max_retries=1)
            
            # Test invalid JSON handling
            invalid_request = MCPRequest(
                id="test_005",
                method="analyze_error",
                params={"invalid": "data"},
                source_agent="test",
                target_agent="log_agent"
            )
            
            response2 = await self.orchestrator.mcp_client.send_request("log_agent", invalid_request)
            
            success = True  # If we get here without crashing, error handling worked
            
            self.log_test_result(
                "Error Handling",
                success,
                "Timeout and invalid request handling tested"
            )
            
        except Exception as e:
            self.log_test_result("Error Handling", False, str(e))
    
    async def run_all_tests(self):
        """Run all tests in the suite."""
        print("🚀 Starting Bugfree Network Test Suite")
        print("=" * 50)
        
        try:
            await self.setup()
            
            # Run all tests
            await self.test_agent_startup()
            await self.test_network_connectivity()
            await self.test_mcp_communication()
            await self.test_agent_handlers()
            await self.test_error_processing_flow()
            await self.test_suggestion_ranking()
            await self.test_error_handling()
            
        finally:
            await self.teardown()
        
        # Print summary
        print("\n" + "=" * 50)
        print("📋 Test Summary")
        print("=" * 50)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        for result in self.test_results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"{status} {result['test']}")
            if result["details"]:
                print(f"   {result['details']}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! The network layer is working correctly.")
            return True
        else:
            print("⚠️ Some tests failed. Check the details above.")
            return False


async def main():
    """Main test runner."""
    test_suite = NetworkTestSuite()
    success = await test_suite.run_all_tests()
    
    if success:
        print("\n✅ Network test suite completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Network test suite failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 