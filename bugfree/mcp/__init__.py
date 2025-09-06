"""MCP (Model Context Protocol) integration for the DevSage debugging system."""

from .client import MCPClient
from .server import MCPServer

__all__ = ["MCPClient", "MCPServer"] 