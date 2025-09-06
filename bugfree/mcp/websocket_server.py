"""WebSocket server for VS Code extension communication."""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Set, List
from datetime import datetime
import websockets
from websockets.server import WebSocketServerProtocol

from ..models.error_models import ErrorContext, FixSuggestion
from ..core.orchestrator import OrchestratorAgent


class BugfreeWebSocketServer:
    """WebSocket server for VS Code extension communication."""
    
    def __init__(self, host: str = "localhost", port: int = 8003):
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.orchestrator: Optional[OrchestratorAgent] = None
        self.running = False
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Suppress websockets library error logging for connection issues
        websockets_logger = logging.getLogger("websockets")
        websockets_logger.setLevel(logging.WARNING)
    
    async def start(self, orchestrator: OrchestratorAgent):
        """Start the WebSocket server."""
        self.orchestrator = orchestrator
        self.running = True
        
        self.logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        
        async with websockets.serve(self._handle_client, self.host, self.port):
            self.logger.info("WebSocket server started successfully")
            await asyncio.Future()  # Run forever
    
    async def stop(self):
        """Stop the WebSocket server."""
        self.running = False
        
        # Close all client connections
        for client in self.clients.copy():
            try:
                await client.close()
            except Exception as e:
                self.logger.error(f"Error closing client connection: {e}")
        
        self.clients.clear()
        self.logger.info("WebSocket server stopped")
    
    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle a new WebSocket client connection."""
        client_id = id(websocket)
        self.clients.add(websocket)
        self.logger.info(f"Client {client_id} connected")
        
        try:
            async for message in websocket:
                await self._process_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"Client {client_id} disconnected")
        except websockets.exceptions.InvalidMessage:
            # Silently ignore invalid WebSocket handshakes (HTTP requests to WebSocket port)
            # This is normal behavior when browsers/tools try to connect
            # Don't log anything - these are not real errors
            pass
        except Exception as e:
            self.logger.error(f"Error handling client {client_id}: {e}")
        finally:
            self.clients.discard(websocket)
    
    async def _process_message(self, websocket: WebSocketServerProtocol, message: str):
        """Process a message from a client."""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "start_system":
                await self._handle_start_system(websocket, data)
            elif message_type == "stop_system":
                await self._handle_stop_system(websocket, data)
            elif message_type == "analyze_error":
                await self._handle_analyze_error(websocket, data)
            elif message_type == "apply_fix":
                await self._handle_apply_fix(websocket, data)
            elif message_type == "ping":
                await self._handle_ping(websocket, data)
            else:
                await self._send_error(websocket, f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            await self._send_error(websocket, "Invalid JSON message")
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            await self._send_error(websocket, f"Internal server error: {str(e)}")
    
    async def _handle_start_system(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]):
        """Handle start system request."""
        try:
            if self.orchestrator:
                # Start the orchestrator and agents
                await self.orchestrator.start()
                
                response = {
                    "type": "system_started",
                    "success": True,
                    "timestamp": datetime.now().isoformat()
                }
                await self._send_message(websocket, response)
                
                # Broadcast to all clients
                await self._broadcast_message({
                    "type": "system_status_changed",
                    "status": "running",
                    "timestamp": datetime.now().isoformat()
                })
            else:
                await self._send_error(websocket, "Orchestrator not available")
                
        except Exception as e:
            self.logger.error(f"Error starting system: {e}")
            await self._send_error(websocket, f"Failed to start system: {str(e)}")
    
    async def _handle_stop_system(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]):
        """Handle stop system request."""
        try:
            if self.orchestrator:
                # Stop the orchestrator and agents
                await self.orchestrator.stop()
                
                response = {
                    "type": "system_stopped",
                    "success": True,
                    "timestamp": datetime.now().isoformat()
                }
                await self._send_message(websocket, response)
                
                # Broadcast to all clients
                await self._broadcast_message({
                    "type": "system_status_changed",
                    "status": "stopped",
                    "timestamp": datetime.now().isoformat()
                })
            else:
                await self._send_error(websocket, "Orchestrator not available")
                
        except Exception as e:
            self.logger.error(f"Error stopping system: {e}")
            await self._send_error(websocket, f"Failed to stop system: {str(e)}")
    
    async def _handle_analyze_error(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]):
        """Handle analyze error request."""
        try:
            if not self.orchestrator:
                await self._send_error(websocket, "System not running")
                return
            
            # Extract error information from request
            file_path = data.get("file")
            line_number = data.get("line")
            error_message = data.get("error_message", "Unknown error")
            
            # Create error context
            error_context = ErrorContext(
                error_type=self._infer_error_type(error_message),
                error_message=error_message,
                file_path=file_path or "unknown",
                line_number=line_number or 1,
                severity=self._infer_severity(error_message),
            )
            
            # Process error through orchestrator
            suggestions = await self.orchestrator.process_error(error_context)
            
            # Send response
            response = {
                "type": "suggestions_ready",
                "error": error_context.model_dump(),
                "suggestions": [s.model_dump() for s in suggestions],
                "timestamp": datetime.now().isoformat()
            }
            await self._send_message(websocket, response)
            
            # Broadcast error detection to all clients
            await self._broadcast_message({
                "type": "error_detected",
                "error": error_context.model_dump(),
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            self.logger.error(f"Error analyzing error: {e}")
            await self._send_error(websocket, f"Failed to analyze error: {str(e)}")
    
    async def _handle_apply_fix(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]):
        """Handle apply fix request."""
        try:
            if not self.orchestrator:
                await self._send_error(websocket, "System not running")
                return
            
            suggestion_data = data.get("suggestion", {})
            
            # Create fix suggestion object
            fix_suggestion = FixSuggestion(
                title=suggestion_data.get("title", "Unknown Fix"),
                description=suggestion_data.get("description", ""),
                code_snippet=suggestion_data.get("code_snippet", ""),
                confidence_score=suggestion_data.get("confidence_score", 0.5),
                agent_source=suggestion_data.get("agent_source", "unknown"),
                explanation=suggestion_data.get("explanation"),
            )
            
            # Apply the fix (this would modify the code in a real implementation)
            success = await self.orchestrator._apply_fix_to_code(fix_suggestion)
            
            response = {
                "type": "fix_applied",
                "success": success,
                "suggestion": fix_suggestion.model_dump(),
                "timestamp": datetime.now().isoformat()
            }
            await self._send_message(websocket, response)
            
            if success:
                # Broadcast fix application to all clients
                await self._broadcast_message({
                    "type": "fix_applied",
                    "suggestion": fix_suggestion.model_dump(),
                    "timestamp": datetime.now().isoformat()
                })
            
        except Exception as e:
            self.logger.error(f"Error applying fix: {e}")
            await self._send_error(websocket, f"Failed to apply fix: {str(e)}")
    
    async def _handle_ping(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]):
        """Handle ping request."""
        response = {
            "type": "pong",
            "timestamp": datetime.now().isoformat(),
            "system_running": self.orchestrator is not None
        }
        await self._send_message(websocket, response)
    
    async def _send_message(self, websocket: WebSocketServerProtocol, message: Dict[str, Any]):
        """Send a message to a specific client."""
        try:
            await websocket.send(json.dumps(message))
        except Exception as e:
            self.logger.error(f"Error sending message to client: {e}")
    
    async def _send_error(self, websocket: WebSocketServerProtocol, error_message: str):
        """Send an error message to a client."""
        error_response = {
            "type": "error",
            "message": error_message,
            "timestamp": datetime.now().isoformat()
        }
        await self._send_message(websocket, error_response)
    
    async def _broadcast_message(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        if not self.clients:
            return
        
        message_json = json.dumps(message)
        disconnected_clients = set()
        
        for client in self.clients:
            try:
                await client.send(message_json)
            except Exception as e:
                self.logger.error(f"Error broadcasting to client: {e}")
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        self.clients -= disconnected_clients
    
    def _infer_error_type(self, error_message: str) -> str:
        """Infer error type from error message."""
        error_message_lower = error_message.lower()
        
        if "nameerror" in error_message_lower or "name" in error_message_lower and "not defined" in error_message_lower:
            return "NAME_ERROR"
        elif "typeerror" in error_message_lower or "type" in error_message_lower:
            return "TYPE_ERROR"
        elif "attributeerror" in error_message_lower or "attribute" in error_message_lower:
            return "ATTRIBUTE_ERROR"
        elif "importerror" in error_message_lower or "module" in error_message_lower and "not found" in error_message_lower:
            return "IMPORT_ERROR"
        elif "syntaxerror" in error_message_lower or "syntax" in error_message_lower:
            return "SYNTAX_ERROR"
        elif "file" in error_message_lower and "not found" in error_message_lower:
            return "FILE_NOT_FOUND"
        elif "index" in error_message_lower and "out of range" in error_message_lower:
            return "INDEX_ERROR"
        elif "keyerror" in error_message_lower or "key" in error_message_lower:
            return "KEY_ERROR"
        else:
            return "UNKNOWN"
    
    def _infer_severity(self, error_message: str) -> str:
        """Infer error severity from error message."""
        error_message_lower = error_message.lower()
        
        if any(keyword in error_message_lower for keyword in ["syntax", "indentation", "import"]):
            return "HIGH"
        elif any(keyword in error_message_lower for keyword in ["type", "attribute", "name"]):
            return "MEDIUM"
        else:
            return "LOW"
    
    async def broadcast_error(self, error_context: ErrorContext):
        """Broadcast an error to all connected clients."""
        message = {
            "type": "error_detected",
            "error": error_context.model_dump(),
            "timestamp": datetime.now().isoformat()
        }
        await self._broadcast_message(message)
    
    async def broadcast_suggestions(self, error_context: ErrorContext, suggestions: List[FixSuggestion]):
        """Broadcast suggestions to all connected clients."""
        message = {
            "type": "suggestions_ready",
            "error": error_context.model_dump(),
            "suggestions": [s.model_dump() for s in suggestions],
            "timestamp": datetime.now().isoformat()
        }
        await self._broadcast_message(message) 