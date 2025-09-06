#!/usr/bin/env python3
"""
Network connectivity validation test
Tests the network connectivity between all agents in the system.
"""

import asyncio
import time
import sys
import os
import socket
from typing import Dict, List, Tuple

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bugfree.core.orchestrator import OrchestratorAgent
from bugfree.agents.log_agent import LogAgent
from bugfree.agents.code_agent import CodeAgent
from bugfree.models.mcp_models import MCPRequest, MCPResponse


class ConnectivityTest:
    """Test network connectivity between agents."""
    
    def __init__(self):
        self.orchestrator = None
        self.log_agent = None
        self.code_agent = None
        self.test_results = []
    
    async def setup(self):
        """Set up the test environment."""
        print("🔧 Setting up connectivity test environment...")
        
        # Initialize agents
        self.orchestrator = OrchestratorAgent()
        self.log_agent = LogAgent()
        self.code_agent = CodeAgent()
        
        # Start agents
        await self.log_agent.start()
        await self.code_agent.start()
        await self.orchestrator.start()
        
        # Wait for connections to establish
        await asyncio.sleep(3)
        
        print("✅ Connectivity test environment ready")
    
    async def teardown(self):
        """Clean up the test environment."""
        print("🧹 Cleaning up connectivity test environment...")
        
        if self.orchestrator:
            await self.orchestrator.stop()
        if self.log_agent:
            await self.log_agent.stop()
        if self.code_agent:
            await self.code_agent.stop()
        
        print("✅ Connectivity test environment cleaned up")
    
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
    
    async def test_port_availability(self):
        """Test that required ports are available."""
        print("\n🔌 Testing Port Availability...")
        
        required_ports = [8000, 8001, 8002]  # Orchestrator, Log Agent, Code Agent
        
        for port in required_ports:
            try:
                # Try to bind to the port
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                sock.close()
                
                if result == 0:
                    self.log_test_result(f"Port {port} Available", True, f"Port {port} is accessible")
                else:
                    self.log_test_result(f"Port {port} Available", False, f"Port {port} is not accessible")
                    
            except Exception as e:
                self.log_test_result(f"Port {port} Available", False, f"Error testing port {port}: {e}")
    
    async def test_agent_connections(self):
        """Test that agents can connect to each other."""
        print("\n🔗 Testing Agent Connections...")
        
        try:
            # Check orchestrator connections
            log_connected = "log_agent" in self.orchestrator.agents and self.orchestrator.agents["log_agent"]["connected"]
            code_connected = "code_agent" in self.orchestrator.agents and self.orchestrator.agents["code_agent"]["connected"]
            
            self.log_test_result(
                "Orchestrator to Log Agent",
                log_connected,
                f"Connection status: {log_connected}"
            )
            
            self.log_test_result(
                "Orchestrator to Code Agent",
                code_connected,
                f"Connection status: {code_connected}"
            )
            
            # Test bidirectional communication
            if log_connected:
                await self.test_bidirectional_communication("log_agent")
            
            if code_connected:
                await self.test_bidirectional_communication("code_agent")
            
        except Exception as e:
            self.log_test_result("Agent Connections", False, str(e))
    
    async def test_bidirectional_communication(self, agent_name: str):
        """Test bidirectional communication with a specific agent."""
        print(f"\n📡 Testing Bidirectional Communication with {agent_name}...")
        
        try:
            # Test request from orchestrator to agent
            test_request = MCPRequest(
                id=f"test_{int(time.time())}",
                method="ping",
                params={"message": "Hello from orchestrator"},
                source_agent="orchestrator",
                target_agent=agent_name,
            )
            
            # Send request
            response = await self.orchestrator.mcp_client.send_request(agent_name, test_request)
            
            success = response is not None
            
            self.log_test_result(
                f"Orchestrator → {agent_name}",
                success,
                f"Response received: {response is not None}"
            )
            
            # Test response handling
            if response:
                self.log_test_result(
                    f"{agent_name} Response Valid",
                    not response.error,
                    f"Response error: {response.error if response.error else 'None'}"
                )
            
        except Exception as e:
            self.log_test_result(f"Bidirectional Communication with {agent_name}", False, str(e))
    
    async def test_connection_stability(self):
        """Test connection stability over time."""
        print("\n🔄 Testing Connection Stability...")
        
        try:
            # Send multiple requests to test stability
            num_requests = 5
            successful_requests = 0
            
            for i in range(num_requests):
                try:
                    test_request = MCPRequest(
                        id=f"stability_test_{i}",
                        method="ping",
                        params={"message": f"Stability test {i}"},
                        source_agent="orchestrator",
                        target_agent="log_agent",
                    )
                    
                    response = await self.orchestrator.mcp_client.send_request("log_agent", test_request)
                    
                    if response and not response.error:
                        successful_requests += 1
                    
                    # Small delay between requests
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    print(f"   Request {i} failed: {e}")
            
            stability_rate = successful_requests / num_requests
            success = stability_rate >= 0.8  # 80% success rate
            
            self.log_test_result(
                "Connection Stability",
                success,
                f"Success rate: {stability_rate:.2%} ({successful_requests}/{num_requests})"
            )
            
        except Exception as e:
            self.log_test_result("Connection Stability", False, str(e))
    
    async def test_timeout_handling(self):
        """Test timeout handling for network operations."""
        print("\n⏱️ Testing Timeout Handling...")
        
        try:
            # Test with a very short timeout
            original_timeout = self.orchestrator.mcp_client.timeout
            self.orchestrator.mcp_client.timeout = 0.1  # 100ms timeout
            
            test_request = MCPRequest(
                id="timeout_test",
                method="slow_operation",
                params={"delay": 1.0},  # 1 second delay
                source_agent="orchestrator",
                target_agent="log_agent",
            )
            
            start_time = time.time()
            response = await self.orchestrator.mcp_client.send_request("log_agent", test_request)
            elapsed_time = time.time() - start_time
            
            # Restore original timeout
            self.orchestrator.mcp_client.timeout = original_timeout
            
            # Should timeout quickly
            success = elapsed_time < 0.5  # Should timeout in less than 500ms
            
            self.log_test_result(
                "Timeout Handling",
                success,
                f"Elapsed time: {elapsed_time:.3f}s (expected < 0.5s)"
            )
            
        except Exception as e:
            self.log_test_result("Timeout Handling", False, str(e))
    
    async def test_retry_logic(self):
        """Test retry logic for failed connections."""
        print("\n🔄 Testing Retry Logic...")
        
        try:
            # Test retry with a non-existent agent
            test_request = MCPRequest(
                id="retry_test",
                method="ping",
                params={"message": "Retry test"},
                source_agent="orchestrator",
                target_agent="non_existent_agent",
            )
            
            # This should fail but not crash
            try:
                response = await self.orchestrator.mcp_client.send_request_with_retry(
                    "non_existent_agent", 
                    test_request, 
                    max_retries=2
                )
                
                # Should return None for non-existent agent
                success = response is None
                
                self.log_test_result(
                    "Retry Logic",
                    success,
                    f"Response: {response} (expected None)"
                )
                
            except Exception as e:
                self.log_test_result("Retry Logic", False, f"Exception: {e}")
            
        except Exception as e:
            self.log_test_result("Retry Logic", False, str(e))
    
    async def test_connection_health_check(self):
        """Test connection health checking."""
        print("\n💓 Testing Connection Health Check...")
        
        try:
            # Test health check for existing connections
            log_healthy = await self.orchestrator.mcp_client.check_connection_health("log_agent")
            code_healthy = await self.orchestrator.mcp_client.check_connection_health("code_agent")
            
            self.log_test_result(
                "Log Agent Health Check",
                log_healthy,
                f"Health status: {log_healthy}"
            )
            
            self.log_test_result(
                "Code Agent Health Check",
                code_healthy,
                f"Health status: {code_healthy}"
            )
            
            # Test health check for non-existent connection
            non_existent_healthy = await self.orchestrator.mcp_client.check_connection_health("non_existent")
            
            self.log_test_result(
                "Non-existent Connection Health Check",
                not non_existent_healthy,  # Should return False
                f"Health status: {non_existent_healthy} (expected False)"
            )
            
        except Exception as e:
            self.log_test_result("Connection Health Check", False, str(e))
    
    async def test_concurrent_connections(self):
        """Test handling of concurrent connections."""
        print("\n⚡ Testing Concurrent Connections...")
        
        try:
            # Send multiple concurrent requests
            num_concurrent = 3
            tasks = []
            
            for i in range(num_concurrent):
                test_request = MCPRequest(
                    id=f"concurrent_test_{i}",
                    method="ping",
                    params={"message": f"Concurrent test {i}"},
                    source_agent="orchestrator",
                    target_agent="log_agent",
                )
                
                task = asyncio.create_task(
                    self.orchestrator.mcp_client.send_request("log_agent", test_request)
                )
                tasks.append(task)
            
            # Wait for all requests to complete
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successful responses
            successful_responses = sum(1 for r in responses if r is not None and not isinstance(r, Exception))
            
            success = successful_responses >= num_concurrent * 0.8  # 80% success rate
            
            self.log_test_result(
                "Concurrent Connections",
                success,
                f"Successful responses: {successful_responses}/{num_concurrent}"
            )
            
        except Exception as e:
            self.log_test_result("Concurrent Connections", False, str(e))
    
    async def run_all_tests(self):
        """Run all connectivity tests."""
        print("🚀 Starting Network Connectivity Tests")
        print("=" * 60)
        
        try:
            await self.setup()
            
            # Run all tests
            await self.test_port_availability()
            await self.test_agent_connections()
            await self.test_connection_stability()
            await self.test_timeout_handling()
            await self.test_retry_logic()
            await self.test_connection_health_check()
            await self.test_concurrent_connections()
            
        finally:
            await self.teardown()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📋 Connectivity Test Summary")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        for result in self.test_results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"{status} {result['test']}")
            if result["details"]:
                print(f"   {result['details']}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All connectivity tests passed! The network is working correctly.")
            return True
        else:
            print("⚠️ Some connectivity tests failed. Check the details above.")
            return False


async def main():
    """Main test runner."""
    connectivity_test = ConnectivityTest()
    success = await connectivity_test.run_all_tests()
    
    if success:
        print("\n✅ Connectivity tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Connectivity tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 