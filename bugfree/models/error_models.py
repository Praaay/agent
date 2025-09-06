"""Data models for error handling and debugging."""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorType(str, Enum):
    """Common error types."""
    SYNTAX_ERROR = "syntax_error"
    RUNTIME_ERROR = "runtime_error"
    IMPORT_ERROR = "import_error"
    MODULE_NOT_FOUND = "module_not_found"
    TYPE_ERROR = "type_error"
    ATTRIBUTE_ERROR = "attribute_error"
    INDEX_ERROR = "index_error"
    KEY_ERROR = "key_error"
    VALUE_ERROR = "value_error"
    NAME_ERROR = "name_error"
    FILE_NOT_FOUND = "file_not_found"
    PERMISSION_ERROR = "permission_error"
    TIMEOUT_ERROR = "timeout_error"
    CONNECTION_ERROR = "connection_error"
    UNKNOWN = "unknown"


class ErrorContext(BaseModel):
    """Context information about an error."""
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
    
    error_type: ErrorType
    error_message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    function_name: Optional[str] = None
    stack_trace: Optional[str] = None
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    timestamp: datetime = Field(default_factory=datetime.now)
    additional_context: Dict[str, Any] = Field(default_factory=dict)
    
    def model_dump(self, *args, **kwargs):
        """Override model_dump to handle datetime serialization."""
        data = super().model_dump(*args, **kwargs)
        if isinstance(data.get('timestamp'), datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        return data


class FixSuggestion(BaseModel):
    """A suggested fix for an error."""
    title: str
    description: str
    code_snippet: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    agent_source: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    explanation: Optional[str] = None
    risks: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)


class AgentResponse(BaseModel):
    """Response from an agent with suggestions."""
    agent_name: str
    error_context: ErrorContext
    suggestions: List[FixSuggestion]
    processing_time: float
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DebugSession(BaseModel):
    """A debugging session containing multiple errors and fixes."""
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
    
    session_id: str
    project_path: str
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    errors: List[ErrorContext] = Field(default_factory=list)
    applied_fixes: List[FixSuggestion] = Field(default_factory=list)
    session_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def model_dump(self, *args, **kwargs):
        """Override model_dump to handle datetime serialization."""
        data = super().model_dump(*args, **kwargs)
        if isinstance(data.get('start_time'), datetime):
            data['start_time'] = data['start_time'].isoformat()
        if isinstance(data.get('end_time'), datetime):
            data['end_time'] = data['end_time'].isoformat()
        return data 