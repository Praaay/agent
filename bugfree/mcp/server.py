"""MCP server for handling incoming requests from other agents."""

import asyncio
import json
import uuid
import socket
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime

from ..models.mcp_models import MCPRequest, MCPResponse


class MCPServer:
    """MCP server for handling incoming requests from other agents."""
    
    def __init__(self, agent_name: str, host: str = "localhost", port: int = 8000):
        self.agent_name = agent_name
        self.host = host
        self.port = port
        self.request_handlers: Dict[str, Callable] = {}
        self.server = None
        self.clients: Dict[str, Any] = {}
        self.running = False
        self.server_task = None
        
    def register_handler(self, method: str, handler: Callable):
        """Register a handler for a specific method."""
        self.request_handlers[method] = handler
    
    async def start(self):
        """Start the MCP server."""
        try:
            # Check if port is available
            if await self._is_port_in_use():
                print(f"Port {self.port} is already in use. Trying alternative port...")
                self.port = await self._find_available_port()
                print(f"Using port {self.port} instead")
            
            self.server = await asyncio.start_server(
                self._handle_client,
                self.host,
                self.port
            )
            self.running = True
            
            print(f"MCP Server for {self.agent_name} started on {self.host}:{self.port}")
            
            # Start server in background
            self.server_task = asyncio.create_task(self._serve_forever())
            
        except Exception as e:
            print(f"Failed to start MCP server: {e}")
            self.running = False
    
    async def _serve_forever(self):
        """Serve the server forever."""
        async with self.server:
            await self.server.serve_forever()
    
    async def _is_port_in_use(self) -> bool:
        """Check if a port is in use."""
        try:
            reader, writer = await asyncio.open_connection(self.host, self.port)
            writer.close()
            await writer.wait_closed()
            return True
        except:
            return False
    
    async def _find_available_port(self) -> int:
        """Find an available port starting from the current port."""
        base_port = self.port
        for port in range(base_port, base_port + 100):
            try:
                reader, writer = await asyncio.open_connection(self.host, port)
                writer.close()
                await writer.wait_closed()
            except:
                return port
        return base_port + 100  # Fallback
    
    async def stop(self):
        """Stop the MCP server."""
        self.running = False
        if self.server_task:
            self.server_task.cancel()
            try:
                await self.server_task
            except asyncio.CancelledError:
                pass
        
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            print(f"MCP Server for {self.agent_name} stopped")
    
    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle incoming client connections with improved error handling."""
        client_addr = writer.get_extra_info('peername')
        client_id = f"{client_addr[0]}:{client_addr[1]}"
        
        print(f"New client connected: {client_id}")
        self.clients[client_id] = {
            "reader": reader,
            "writer": writer,
            "connected": True,
            "last_activity": datetime.now(),
        }
        
        try:
            while self.running and self.clients[client_id]["connected"]:
                # Read request data with timeout
                try:
                    data = await asyncio.wait_for(reader.read(1024), timeout=30.0)
                    if not data:
                        break
                    
                    # Update last activity
                    self.clients[client_id]["last_activity"] = datetime.now()
                    
                except asyncio.TimeoutError:
                    print(f"Client {client_id} timeout, disconnecting")
                    break
                
                # Parse request
                try:
                    request_data = json.loads(data.decode('utf-8'))
                    request = MCPRequest(**request_data)
                    
                    # Handle request
                    response = await self._process_request(request)
                    
                    # Send response with timeout
                    try:
                        response_data = json.dumps(response.model_dump()).encode('utf-8')
                        writer.write(response_data)
                        await asyncio.wait_for(writer.drain(), timeout=10.0)
                    except asyncio.TimeoutError:
                        print(f"Response timeout to client {client_id}")
                        break
                    
                except json.JSONDecodeError as e:
                    print(f"Invalid JSON from client {client_id}: {e}")
                    # Send error response
                    error_response = MCPResponse(
                        id=str(uuid.uuid4()),
                        request_id="unknown",
                        error={"code": "invalid_json", "message": "Invalid JSON format"},
                        source_agent=self.agent_name,
                        target_agent="unknown",
                    )
                    try:
                        error_data = json.dumps(error_response.model_dump()).encode('utf-8')
                        writer.write(error_data)
                        await asyncio.wait_for(writer.drain(), timeout=5.0)
                    except:
                        pass
                    break
                except Exception as e:
                    print(f"Error processing request from client {client_id}: {e}")
                    # Send error response
                    error_response = MCPResponse(
                        id=str(uuid.uuid4()),
                        request_id="unknown",
                        error={"code": "processing_error", "message": str(e)},
                        source_agent=self.agent_name,
                        target_agent="unknown",
                    )
                    try:
                        error_data = json.dumps(error_response.model_dump()).encode('utf-8')
                        writer.write(error_data)
                        await asyncio.wait_for(writer.drain(), timeout=5.0)
                    except:
                        pass
                    break
                    
        except Exception as e:
            print(f"Error handling client {client_id}: {e}")
        finally:
            # Clean up client connection
            if client_id in self.clients:
                del self.clients[client_id]
            try:
                writer.close()
                await asyncio.wait_for(writer.wait_closed(), timeout=5.0)
            except:
                pass
            print(f"Client disconnected: {client_id}")
    
    async def _process_request(self, request: MCPRequest) -> MCPResponse:
        """Process an incoming request with improved error handling."""
        if request.method in self.request_handlers:
            try:
                # Add timeout to handler execution
                result = await asyncio.wait_for(
                    self.request_handlers[request.method](request),
                    timeout=30.0
                )
                return MCPResponse(
                    id=str(uuid.uuid4()),
                    request_id=request.id,
                    result=result,
                    source_agent=self.agent_name,
                    target_agent=request.source_agent,
                )
            except asyncio.TimeoutError:
                return MCPResponse(
                    id=str(uuid.uuid4()),
                    request_id=request.id,
                    error={"code": "handler_timeout", "message": "Handler execution timed out"},
                    source_agent=self.agent_name,
                    target_agent=request.source_agent,
                )
            except Exception as e:
                return MCPResponse(
                    id=str(uuid.uuid4()),
                    request_id=request.id,
                    error={"code": "handler_error", "message": str(e)},
                    source_agent=self.agent_name,
                    target_agent=request.source_agent,
                )
        else:
            return MCPResponse(
                id=str(uuid.uuid4()),
                request_id=request.id,
                error={"code": "method_not_found", "message": f"Method {request.method} not found"},
                source_agent=self.agent_name,
                target_agent=request.source_agent,
            )
    
    async def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        message_data = json.dumps(message).encode('utf-8')
        
        for client_id, client_info in list(self.clients.items()):
            if client_info["connected"]:
                try:
                    client_info["writer"].write(message_data)
                    await client_info["writer"].drain()
                except Exception as e:
                    print(f"Failed to send message to client {client_id}: {e}")
                    client_info["connected"] = False
    
    def get_connected_clients(self) -> List[str]:
        """Get list of connected client IDs."""
        return [client_id for client_id, client_info in self.clients.items() 
                if client_info["connected"]]
    
    def is_running(self) -> bool:
        """Check if the server is running."""
        return self.running
    
    def get_port(self) -> int:
        """Get the current port being used."""
        return self.port


class SimpleMCPServer:
    """A simplified MCP server for testing and development."""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.request_handlers: Dict[str, Callable] = {}
        self.message_queue: List[Dict[str, Any]] = []
    
    def register_handler(self, method: str, handler: Callable):
        """Register a handler for a specific method."""
        self.request_handlers[method] = handler
    
    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """Handle an incoming request."""
        if request.method in self.request_handlers:
            try:
                result = await self.request_handlers[request.method](request)
                return MCPResponse(
                    id=str(uuid.uuid4()),
                    request_id=request.id,
                    result=result,
                    source_agent=self.agent_name,
                    target_agent=request.source_agent,
                )
            except Exception as e:
                return MCPResponse(
                    id=str(uuid.uuid4()),
                    request_id=request.id,
                    error={"code": "handler_error", "message": str(e)},
                    source_agent=self.agent_name,
                    target_agent=request.source_agent,
                )
        else:
            return MCPResponse(
                id=str(uuid.uuid4()),
                request_id=request.id,
                error={"code": "method_not_found", "message": f"Method {request.method} not found"},
                source_agent=self.agent_name,
                target_agent=request.source_agent,
            )
    
    def add_message(self, message: Dict[str, Any]):
        """Add a message to the queue."""
        self.message_queue.append(message)
    
    def get_messages(self) -> List[Dict[str, Any]]:
        """Get all messages from the queue."""
        messages = self.message_queue.copy()
        self.message_queue.clear()
        return messages 