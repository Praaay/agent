#!/usr/bin/env python3
"""
Bugfree CLI - Send errors to the running Bugfree system for analysis.
"""

import asyncio
import json
import sys
import subprocess
import uuid
from typing import Optional
from datetime import datetime

from bugfree.models.error_models import ErrorContext, ErrorType, ErrorSeverity
from bugfree.mcp.client import MCPClient


class BugfreeCLI:
    """CLI tool for interacting with the Bugfree system."""
    
    def __init__(self):
        self.orchestrator_client = MCPClient("bugfree_cli")
    
    async def connect(self):
        """Connect to the orchestrator."""
        try:
            connection_info = {
                "host": "localhost",
                "port": 8000
            }
            await self.orchestrator_client.connect_to_agent("orchestrator", connection_info)
            print("✅ Connected to Bugfree system")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to Bugfree system: {e}")
            return False
    
    async def analyze_error(self, error_message: str, file_path: str = "unknown", line_number: int = 1):
        """Send an error to the Bugfree system for analysis."""
        try:
            # Create error context
            error_context = ErrorContext(
                error_type=self._extract_error_type(error_message),
                error_message=error_message,
                file_path=file_path,
                line_number=line_number,
                severity=ErrorSeverity.HIGH,
                timestamp=datetime.now().isoformat(),
            )
            
            # Send to orchestrator for analysis
            from bugfree.models.mcp_models import MCPRequest
            
            request = MCPRequest(
                id=str(uuid.uuid4()),
                method="process_error",
                params={
                    "error_context": error_context.model_dump()
                },
                source_agent="bugfree_cli",
                target_agent="orchestrator"
            )
            
            response = await self.orchestrator_client.send_request("orchestrator", request)
            
            if response and response.result:
                suggestions = response.result.get("suggestions", [])
                print(f"✅ Bugfree analyzed the error and found {len(suggestions)} suggestions:")
                
                for i, suggestion in enumerate(suggestions, 1):
                    print(f"\n💡 Suggestion {i}:")
                    print(f"   Title: {suggestion.get('title', 'Unknown')}")
                    print(f"   Agent: {suggestion.get('agent_source', 'unknown')}")
                    print(f"   Confidence: {suggestion.get('confidence_score', 0) * 100:.0f}%")
                    print(f"   Description: {suggestion.get('description', 'No description')}")
                    print(f"   Code: {suggestion.get('code_snippet', 'No code')}")
            elif response and response.error:
                print(f"❌ Bugfree returned an error: {response.error}")
            else:
                print("❌ No suggestions received from Bugfree system")
                
        except Exception as e:
            print(f"❌ Error analyzing error: {e}")
    
    def _extract_error_type(self, error_message: str) -> ErrorType:
        """Extract error type from error message."""
        error_lower = error_message.lower()
        
        if "nameerror" in error_lower:
            return ErrorType.NAME_ERROR
        elif "typeerror" in error_lower:
            return ErrorType.TYPE_ERROR
        elif "attributeerror" in error_lower:
            return ErrorType.ATTRIBUTE_ERROR
        elif "importerror" in error_lower:
            return ErrorType.IMPORT_ERROR
        elif "syntaxerror" in error_lower:
            return ErrorType.SYNTAX_ERROR
        elif "filenotfounderror" in error_lower:
            return ErrorType.FILE_NOT_FOUND
        elif "indexerror" in error_lower:
            return ErrorType.INDEX_ERROR
        elif "keyerror" in error_lower:
            return ErrorType.KEY_ERROR
        elif "valueerror" in error_lower:
            return ErrorType.VALUE_ERROR
        elif "zerodivisionerror" in error_lower:
            return ErrorType.ZERO_DIVISION_ERROR
        else:
            return ErrorType.UNKNOWN
    
    async def run_and_analyze(self, script_path: str):
        """Run a Python script and analyze any errors that occur."""
        print(f"🚀 Running {script_path}...")
        
        try:
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"❌ Error detected in {script_path}")
                print(f"Error: {result.stderr.strip()}")
                
                # Analyze the error
                await self.analyze_error(result.stderr.strip(), script_path)
            else:
                print(f"✅ {script_path} ran successfully")
                
        except subprocess.TimeoutExpired:
            print(f"❌ {script_path} timed out")
        except Exception as e:
            print(f"❌ Error running {script_path}: {e}")
    
    async def close(self):
        """Close the connection."""
        await self.orchestrator_client.close()


async def main():
    """Main CLI function."""
    if len(sys.argv) < 2:
        print("Usage: python bugfree_cli.py <command> [args...]")
        print("\nCommands:")
        print("  run <script.py>     - Run a Python script and analyze errors")
        print("  analyze <error>     - Analyze a specific error message")
        print("  test               - Run test_errors.py and analyze")
        return
    
    command = sys.argv[1]
    cli = BugfreeCLI()
    
    try:
        if not await cli.connect():
            return
        
        if command == "run" and len(sys.argv) >= 3:
            script_path = sys.argv[2]
            await cli.run_and_analyze(script_path)
            
        elif command == "analyze" and len(sys.argv) >= 3:
            error_message = sys.argv[2]
            await cli.analyze_error(error_message)
            
        elif command == "test":
            await cli.run_and_analyze("test_errors.py")
            
        else:
            print("Invalid command. Use 'run', 'analyze', or 'test'")
            
    finally:
        await cli.close()


if __name__ == "__main__":
    asyncio.run(main()) 