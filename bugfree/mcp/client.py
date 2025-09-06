"""MCP client for agent communication."""

import asyncio
import json
import uuid
import socket
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..models.mcp_models import MCPRequest, MCPResponse, ErrorAnalysisRequest, CodeContextRequest


class MCPClient:
    """MCP client for sending requests to other agents."""
    
    def __init__(self, agent_name: str, timeout: float = 10.0, max_retries: int = 3):
        self.agent_name = agent_name
        self.connections: Dict[str, Dict[str, Any]] = {}
        self.request_handlers: Dict[str, callable] = {}
        self.timeout = timeout
        self.max_retries = max_retries
        self.connection_locks: Dict[str, asyncio.Lock] = {}
    
    async def connect_to_agent(self, agent_name: str, connection_info: Dict[str, Any]) -> bool:
        """Connect to another agent with timeout and retry logic."""
        for attempt in range(self.max_retries):
            try:
                host = connection_info.get("host", "localhost")
                port = connection_info.get("port", 8000)
                
                # Test the connection with timeout
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=self.timeout
                )
                
                # Store connection info
                self.connections[agent_name] = {
                    "connected": True,
                    "connection_info": connection_info,
                    "reader": reader,
                    "writer": writer,
                    "last_heartbeat": datetime.now(),
                    "connection_time": datetime.now(),
                }
                
                # Create a lock for this connection
                self.connection_locks[agent_name] = asyncio.Lock()
                
                print(f"Connected to {agent_name} at {host}:{port}")
                return True
                
            except asyncio.TimeoutError:
                print(f"Connection timeout to {agent_name} (attempt {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)  # Wait before retry
            except Exception as e:
                print(f"Failed to connect to agent {agent_name} (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)  # Wait before retry
        
        return False
    
    async def send_request(self, target_agent: str, request: MCPRequest) -> Optional[MCPResponse]:
        """Send a request to another agent with timeout handling."""
        if target_agent not in self.connections:
            raise ValueError(f"Not connected to agent {target_agent}")
        
        # Get the lock for this connection
        lock = self.connection_locks.get(target_agent)
        if not lock:
            print(f"No lock found for {target_agent}, creating one")
            lock = asyncio.Lock()
            self.connection_locks[target_agent] = lock
        
        async with lock:  # Ensure only one request at a time per connection
            try:
                connection = self.connections[target_agent]
                writer = connection["writer"]
                
                # Send request - ensure proper serialization
                request_dict = request.model_dump()
                request_data = json.dumps(request_dict).encode('utf-8')
                writer.write(request_data)
                await asyncio.wait_for(writer.drain(), timeout=self.timeout)
                
                # Read response with timeout
                reader = connection["reader"]
                data = await asyncio.wait_for(reader.read(4096), timeout=self.timeout)
                
                if data:
                    response_data = json.loads(data.decode('utf-8'))
                    return MCPResponse(**response_data)
                else:
                    print(f"No response from {target_agent}")
                    return None
                    
            except asyncio.TimeoutError:
                print(f"Request timeout to {target_agent}")
                # Mark connection as failed
                if target_agent in self.connections:
                    self.connections[target_agent]["connected"] = False
                return None
            except Exception as e:
                print(f"Failed to send request to {target_agent}: {e}")
                # Mark connection as failed
                if target_agent in self.connections:
                    self.connections[target_agent]["connected"] = False
                return None
    
    async def broadcast_error(self, error_context: Dict[str, Any]) -> List[MCPResponse]:
        """Broadcast an error to all connected agents."""
        responses = []
        
        for agent_name in self.connections:
            if self.connections[agent_name]["connected"]:
                request = ErrorAnalysisRequest(
                    id=str(uuid.uuid4()),
                    source_agent=self.agent_name,
                    target_agent=agent_name,
                    error_context=error_context,
                )
                
                response = await self.send_request(agent_name, request)
                if response:
                    responses.append(response)
        
        return responses
    
    async def request_code_context(self, target_agent: str, file_path: str, line_number: Optional[int] = None) -> Optional[MCPResponse]:
        """Request code context from another agent."""
        request = CodeContextRequest(
            id=str(uuid.uuid4()),
            source_agent=self.agent_name,
            target_agent=target_agent,
            file_path=file_path,
            line_number=line_number,
        )
        
        return await self.send_request(target_agent, request)
    
    def register_request_handler(self, method: str, handler: callable):
        """Register a handler for incoming requests."""
        self.request_handlers[method] = handler
    
    async def handle_incoming_request(self, request: MCPRequest) -> MCPResponse:
        """Handle an incoming request from another agent."""
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
    
    async def close(self):
        """Close all connections."""
        agent_names = list(self.connections.keys())
        for agent_name in agent_names:
            try:
                await self.disconnect_from_agent(agent_name)
            except Exception as e:
                print(f"Error disconnecting from {agent_name}: {e}")
    
    async def disconnect_from_agent(self, agent_name: str):
        """Disconnect from an agent."""
        try:
            if agent_name in self.connections:
                connection = self.connections[agent_name]
                if "writer" in connection:
                    connection["writer"].close()
                    await connection["writer"].wait_closed()
                del self.connections[agent_name]
        except KeyError:
            pass  # Already removed
        except Exception as e:
            print(f"Error disconnecting from {agent_name}: {e}")
        
        # Clean up the connection lock
        try:
            if agent_name in self.connection_locks:
                del self.connection_locks[agent_name]
        except KeyError:
            pass  # Already removed
        except Exception as e:
            print(f"Error removing lock for {agent_name}: {e}")
    
    async def send_request_with_retry(self, target_agent: str, request: MCPRequest, max_retries: int = None) -> Optional[MCPResponse]:
        """Send a request with retry logic."""
        if max_retries is None:
            max_retries = self.max_retries
            
        for attempt in range(max_retries):
            try:
                response = await self.send_request(target_agent, request)
                if response:
                    return response
            except Exception as e:
                print(f"Attempt {attempt + 1} failed for {target_agent}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)  # Wait before retry
        return None
    
    async def check_connection_health(self, agent_name: str) -> bool:
        """Check if connection to an agent is healthy."""
        if agent_name not in self.connections:
            return False
        
        connection = self.connections[agent_name]
        if not connection["connected"]:
            return False
        
        # Check if connection is too old (more than 5 minutes)
        connection_time = connection.get("connection_time")
        if connection_time and (datetime.now() - connection_time).total_seconds() > 300:
            print(f"Connection to {agent_name} is too old, reconnecting...")
            await self.disconnect_from_agent(agent_name)
            return await self.connect_to_agent(agent_name, connection["connection_info"])
        
        return True 