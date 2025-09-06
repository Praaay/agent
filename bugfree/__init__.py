"""
Bugfree Multi-Agent Debugging System

A sophisticated multi-agent debugging system that uses specialized AI agents to diagnose,
explain, and suggest fixes for runtime errors through MCP integration.
"""

__version__ = "0.1.0"
__author__ = "Bugfree Team"

from .core.orchestrator import OrchestratorAgent
from .agents.log_agent import LogAgent
from .agents.code_agent import CodeAgent

__all__ = [
    "OrchestratorAgent",
    "LogAgent", 
    "CodeAgent",
] 