"""Orchestrator Agent for coordinating between all agents and ranking suggestions."""

import asyncio
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models.error_models import ErrorContext, FixSuggestion, AgentResponse, DebugSession
from ..models.mcp_models import MCPRequest, MCPResponse, ErrorAnalysisRequest
from ..mcp.client import MCPClient
from ..mcp.server import MCPServer


class OrchestratorAgent:
    """Orchestrator agent that coordinates between all agents and ranks suggestions."""
    
    def __init__(self, name: str = "orchestrator"):
        self.name = name
        self.mcp_client = MCPClient(name)
        self.mcp_server = MCPServer(name, host="localhost", port=8000)
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.active_sessions: Dict[str, DebugSession] = {}
        self.suggestion_history: List[FixSuggestion] = []
        
        # Register MCP handlers
        self.mcp_server.register_handler("process_error", self._handle_process_error)
        self.mcp_server.register_handler("get_suggestions", self._handle_get_suggestions)
        self.mcp_server.register_handler("apply_fix", self._handle_apply_fix)
        self.mcp_server.register_handler("get_session_status", self._handle_get_session_status)
    
    async def start(self):
        """Start the orchestrator agent."""
        print(f"Orchestrator Agent {self.name} started")
        
        # Start MCP server in background
        asyncio.create_task(self.mcp_server.start())
        
        # Wait a moment for server to start
        await asyncio.sleep(1)
        
        # Connect to other agents
        await self._connect_to_agents()
    
    async def stop(self):
        """Stop the orchestrator agent."""
        await self.mcp_server.stop()
        await self.mcp_client.close()
        print(f"Orchestrator Agent {self.name} stopped")
    
    async def _connect_to_agents(self):
        """Connect to other agents in the system."""
        # Connect to Log Agent
        log_connected = await self.mcp_client.connect_to_agent("log_agent", {"host": "localhost", "port": 8001})
        if log_connected:
            self.agents["log_agent"] = {"connected": True, "last_heartbeat": datetime.now()}
            print("Connected to Log Agent")
        else:
            print("Failed to connect to Log Agent")
        
        # Connect to Code Agent
        code_connected = await self.mcp_client.connect_to_agent("code_agent", {"host": "localhost", "port": 8002})
        if code_connected:
            self.agents["code_agent"] = {"connected": True, "last_heartbeat": datetime.now()}
            print("Connected to Code Agent")
        else:
            print("Failed to connect to Code Agent")
        
        connected_count = sum(1 for agent in self.agents.values() if agent["connected"])
        print(f"Connected to {connected_count} agents")
    
    async def process_error(self, error_context: ErrorContext) -> List[FixSuggestion]:
        """Process an error and get ranked suggestions from all agents."""
        start_time = time.time()
        
        # Create or get debug session
        session_id = f"session_{int(time.time())}"
        if not self.active_sessions:
            session = DebugSession(
                session_id=session_id,
                project_path=error_context.file_path or "unknown",
            )
            self.active_sessions[session_id] = session
        else:
            session = list(self.active_sessions.values())[0]
            session_id = session.session_id
        
        # Add error to session
        session.errors.append(error_context)
        
        # Collect suggestions from all agents
        all_suggestions = await self._collect_suggestions(error_context)
        
        # Rank and filter suggestions
        ranked_suggestions = await self._rank_suggestions(all_suggestions, error_context)
        
        # Update session
        session.applied_fixes.extend(ranked_suggestions[:3])  # Top 3 suggestions
        
        # Store in history
        self.suggestion_history.extend(ranked_suggestions)
        
        processing_time = time.time() - start_time
        print(f"Processed error in {processing_time:.2f}s, found {len(ranked_suggestions)} suggestions")
        
        return ranked_suggestions[:3]  # Return top 3 suggestions
    
    async def _collect_suggestions(self, error_context: ErrorContext) -> List[FixSuggestion]:
        """Collect suggestions from all connected agents."""
        all_suggestions = []
        
        # Prepare error data for MCP
        error_data = error_context.model_dump()
        
        # Request suggestions from Log Agent
        if "log_agent" in self.agents and self.agents["log_agent"]["connected"]:
            try:
                log_response = await self._request_from_agent("log_agent", "analyze_error", {
                    "error_context": error_data
                })
                
                if log_response and log_response.result:
                    suggestions = log_response.result.get("suggestions", [])
                    for suggestion in suggestions:
                        fix_suggestion = FixSuggestion(
                            title=suggestion.get("title", "Log Analysis Suggestion"),
                            description=suggestion.get("description", ""),
                            code_snippet=suggestion.get("code_snippet", ""),
                            confidence_score=suggestion.get("confidence_score", 0.5),
                            agent_source="log_agent",
                            explanation=suggestion.get("explanation"),
                        )
                        all_suggestions.append(fix_suggestion)
                        
            except Exception as e:
                print(f"Error getting suggestions from Log Agent: {e}")
        
        # Request suggestions from Code Agent
        if "code_agent" in self.agents and self.agents["code_agent"]["connected"]:
            try:
                code_response = await self._request_from_agent("code_agent", "suggest_fixes", {
                    "error_context": error_data
                })
                
                if code_response and code_response.result:
                    suggestions = code_response.result.get("suggestions", [])
                    for suggestion in suggestions:
                        fix_suggestion = FixSuggestion(
                            title=suggestion.get("title", "Code Analysis Suggestion"),
                            description=suggestion.get("description", ""),
                            code_snippet=suggestion.get("code_snippet", ""),
                            confidence_score=suggestion.get("confidence_score", 0.5),
                            agent_source="code_agent",
                            explanation=suggestion.get("explanation"),
                        )
                        all_suggestions.append(fix_suggestion)
                        
            except Exception as e:
                print(f"Error getting suggestions from Code Agent: {e}")
        
        return all_suggestions
    
    async def _rank_suggestions(self, suggestions: List[FixSuggestion], error_context: ErrorContext) -> List[FixSuggestion]:
        """Rank suggestions by confidence and relevance."""
        if not suggestions:
            return []
        
        # Calculate ranking scores for each suggestion
        ranked_suggestions = []
        for suggestion in suggestions:
            score = self._calculate_suggestion_score(suggestion, error_context)
            ranked_suggestions.append((suggestion, score))
        
        # Sort by score (highest first)
        ranked_suggestions.sort(key=lambda x: x[1], reverse=True)
        
        # Return top suggestions
        return [suggestion for suggestion, score in ranked_suggestions[:5]]
    
    def _calculate_suggestion_score(self, suggestion: FixSuggestion, error_context: ErrorContext) -> float:
        """Calculate a ranking score for a suggestion."""
        base_score = suggestion.confidence_score
        
        # Agent-specific weighting
        agent_weights = {
            "code_agent": 1.2,      # Code agent gets 20% boost
            "log_agent": 1.1,       # Log agent gets 10% boost
            "orchestrator": 1.0,    # Base weight
        }
        
        agent_weight = agent_weights.get(suggestion.agent_source, 1.0)
        weighted_score = base_score * agent_weight
        
        # Error type matching bonus
        if self._suggestion_matches_error_type(suggestion, error_context):
            weighted_score += 0.1
        
        # Code snippet quality bonus
        if suggestion.code_snippet and len(suggestion.code_snippet.strip()) > 10:
            weighted_score += 0.05
        
        # Explanation quality bonus
        if suggestion.explanation and len(suggestion.explanation) > 20:
            weighted_score += 0.05
        
        return min(weighted_score, 1.0)  # Cap at 1.0
    
    def _suggestion_matches_error_type(self, suggestion: FixSuggestion, error_context: ErrorContext) -> bool:
        """Check if suggestion title/description matches the error type."""
        error_type = error_context.error_type.value.lower()
        suggestion_text = f"{suggestion.title} {suggestion.description}".lower()
        
        # Check for error type keywords in suggestion
        error_keywords = {
            "name_error": ["name", "variable", "defined", "undefined"],
            "import_error": ["import", "module", "install"],
            "attribute_error": ["attribute", "method", "dir"],
            "type_error": ["type", "argument", "parameter"],
            "index_error": ["index", "list", "range"],
            "key_error": ["key", "dictionary", "get"],
            "file_not_found": ["file", "path", "exists"],
        }
        
        if error_type in error_keywords:
            keywords = error_keywords[error_type]
            return any(keyword in suggestion_text for keyword in keywords)
        
        return False
    
    async def _handle_process_error(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle process error request from other agents."""
        try:
            error_context_data = request.params.get("error_context", {})
            error_context = ErrorContext(**error_context_data)
            
            # Process the error
            suggestions = await self.process_error(error_context)
            
            return {
                "suggestions": [s.model_dump() for s in suggestions],
                "session_id": list(self.active_sessions.keys())[0] if self.active_sessions else None,
                "processing_time": 0.5,
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _handle_get_suggestions(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle get suggestions request from other agents."""
        try:
            session_id = request.params.get("session_id")
            
            if session_id and session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                suggestions = session.applied_fixes[-5:]  # Last 5 suggestions
                return {
                    "suggestions": [s.model_dump() for s in suggestions],
                    "session_status": "active",
                }
            else:
                return {
                    "suggestions": [],
                    "session_status": "not_found",
                }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _handle_apply_fix(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle apply fix request from other agents."""
        try:
            fix_data = request.params.get("fix_suggestion", {})
            session_id = request.params.get("session_id")
            
            # Create fix suggestion object
            fix_suggestion = FixSuggestion(**fix_data)
            
            # Apply the fix (in a real implementation, this would modify the code)
            success = await self._apply_fix_to_code(fix_suggestion)
            
            # Track the applied fix
            if session_id and session_id in self.active_sessions:
                self.active_sessions[session_id].applied_fixes.append(fix_suggestion)
            
            return {
                "success": success,
                "message": "Fix applied successfully" if success else "Failed to apply fix",
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _handle_get_session_status(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle get session status request from other agents."""
        try:
            session_id = request.params.get("session_id")
            
            if session_id and session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                return {
                    "session_id": session.session_id,
                    "project_path": session.project_path,
                    "start_time": session.start_time.isoformat(),
                    "error_count": len(session.errors),
                    "fix_count": len(session.applied_fixes),
                    "status": "active",
                }
            else:
                return {
                    "status": "not_found",
                    "message": "Session not found",
                }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _apply_fix_to_code(self, fix_suggestion: FixSuggestion) -> bool:
        """Apply a fix suggestion to the code (placeholder implementation)."""
        try:
            # In a real implementation, this would:
            # 1. Parse the code file
            # 2. Apply the suggested changes
            # 3. Validate the changes
            # 4. Save the file
            
            print(f"Applying fix: {fix_suggestion.title}")
            print(f"Code snippet: {fix_suggestion.code_snippet}")
            
            # For now, just return success
            return True
            
        except Exception as e:
            print(f"Error applying fix: {e}")
            return False
    
    async def _request_from_agent(self, agent_name: str, method: str, params: Dict[str, Any]) -> Optional[MCPResponse]:
        """Send a request to a specific agent with improved error handling."""
        try:
            # Check connection health first
            if not await self.mcp_client.check_connection_health(agent_name):
                print(f"Connection to {agent_name} is unhealthy, attempting to reconnect...")
                connection_info = {"host": "localhost", "port": 8001 if agent_name == "log_agent" else 8002}
                await self.mcp_client.connect_to_agent(agent_name, connection_info)
            
            request = MCPRequest(
                id=f"req_{int(time.time())}",
                method=method,
                params=params,
                source_agent=self.name,
                target_agent=agent_name,
            )
            
            # Use retry logic
            response = await self.mcp_client.send_request_with_retry(agent_name, request)
            return response
            
        except Exception as e:
            print(f"Error requesting from {agent_name}: {e}")
            return None
    
    async def _check_historical_success(self, suggestion: FixSuggestion) -> bool:
        """Check if similar suggestions were successful in the past."""
        # Simple check for now - in a real system, this would query a database
        similar_suggestions = [
            s for s in self.suggestion_history
            if s.title == suggestion.title and s.agent_source == suggestion.agent_source
        ]
        
        return len(similar_suggestions) > 0
    
    def get_active_sessions(self) -> List[DebugSession]:
        """Get all active debug sessions."""
        return list(self.active_sessions.values())
    
    def get_suggestion_history(self) -> List[FixSuggestion]:
        """Get suggestion history."""
        return self.suggestion_history.copy()
    
    async def connect_to_agent(self, agent_name: str, connection_info: Dict[str, Any]):
        """Connect to another agent."""
        success = await self.mcp_client.connect_to_agent(agent_name, connection_info)
        if success:
            self.agents[agent_name] = {
                "connected": True,
                "last_heartbeat": datetime.now(),
                "connection_info": connection_info,
            }
        return success 