"""MCP (Model Context Protocol) data models."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict


class MCPMessage(BaseModel):
    """Base MCP message."""
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
    
    id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    source: str
    destination: str
    message_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    
    def model_dump(self, *args, **kwargs):
        """Override model_dump to handle datetime serialization."""
        data = super().model_dump(*args, **kwargs)
        if isinstance(data.get('timestamp'), datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        return data


class MCPRequest(BaseModel):
    """MCP request message."""
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
    
    id: str
    method: str
    params: Dict[str, Any] = Field(default_factory=dict)
    source_agent: str
    target_agent: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    def model_dump(self, *args, **kwargs):
        """Override model_dump to handle datetime serialization."""
        data = super().model_dump(*args, **kwargs)
        if isinstance(data.get('timestamp'), datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        return data


class MCPResponse(BaseModel):
    """MCP response message."""
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
    
    id: str
    request_id: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    source_agent: str
    target_agent: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    def model_dump(self, *args, **kwargs):
        """Override model_dump to handle datetime serialization."""
        data = super().model_dump(*args, **kwargs)
        if isinstance(data.get('timestamp'), datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        return data


class ErrorAnalysisRequest(MCPRequest):
    """Request for error analysis."""
    method: str = "analyze_error"
    error_context: Dict[str, Any]
    file_content: Optional[str] = None
    project_context: Optional[Dict[str, Any]] = None


class ErrorAnalysisResponse(MCPResponse):
    """Response with error analysis."""
    suggestions: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    processing_time: float


class CodeContextRequest(MCPRequest):
    """Request for code context."""
    method: str = "get_code_context"
    file_path: str
    line_number: Optional[int] = None
    context_lines: int = 10


class CodeContextResponse(MCPResponse):
    """Response with code context."""
    file_content: str
    surrounding_code: str
    imports: List[str] = Field(default_factory=list)
    function_context: Optional[str] = None
    class_context: Optional[str] = None


class FixVerificationRequest(MCPRequest):
    """Request for fix verification."""
    method: str = "verify_fix"
    original_error: Dict[str, Any]
    suggested_fix: Dict[str, Any]
    test_context: Optional[Dict[str, Any]] = None


class FixVerificationResponse(MCPResponse):
    """Response with fix verification results."""
    is_safe: bool
    confidence: float = Field(ge=0.0, le=1.0)
    risks: List[str] = Field(default_factory=list)
    test_results: Optional[Dict[str, Any]] = None 