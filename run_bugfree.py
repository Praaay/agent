#!/usr/bin/env python3
"""
Simple script to run the Bugfree system and keep it running.
"""

import asyncio
import signal
import sys
from bugfree.core.orchestrator import OrchestratorAgent
from bugfree.agents.log_agent import LogAgent
from bugfree.agents.code_agent import CodeAgent
from bugfree.mcp.websocket_server import BugfreeWebSocketServer


class BugfreeRunner:
    def __init__(self):
        self.orchestrator = OrchestratorAgent()
        self.log_agent = LogAgent()
        self.code_agent = CodeAgent()
        self.websocket_server = BugfreeWebSocketServer()
        self.running = False
        
    async def start(self):
        """Start all components."""
        print("🚀 Starting Bugfree Multi-Agent System...")
        
        # Start agents
        await self.log_agent.start()
        print("✅ Log Agent started")
        
        await self.code_agent.start()
        print("✅ Code Agent started")
        
        await self.orchestrator.start()
        print("✅ Orchestrator started")
        
        # Start WebSocket server
        print("🌐 Starting WebSocket server...")
        websocket_task = asyncio.create_task(
            self.websocket_server.start(self.orchestrator)
        )
        
        self.running = True
        print("🎉 Bugfree system is running!")
        print("📡 WebSocket server listening on localhost:8000")
        print("🔗 VS Code extension can now connect")
        print("⏹️  Press Ctrl+C to stop")
        
        try:
            # Keep the system running
            await websocket_task
        except asyncio.CancelledError:
            print("\n🛑 Shutting down...")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop all components."""
        if not self.running:
            return
            
        print("🛑 Stopping Bugfree system...")
        
        await self.websocket_server.stop()
        await self.orchestrator.stop()
        await self.code_agent.stop()
        await self.log_agent.stop()
        
        self.running = False
        print("✅ Bugfree system stopped")


async def main():
    """Main function."""
    runner = BugfreeRunner()
    
    # Handle Ctrl+C gracefully
    def signal_handler(signum, frame):
        print("\n🛑 Received interrupt signal")
        asyncio.create_task(runner.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        await runner.start()
    except KeyboardInterrupt:
        print("\n🛑 Keyboard interrupt received")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await runner.stop()


if __name__ == "__main__":
    asyncio.run(main()) 