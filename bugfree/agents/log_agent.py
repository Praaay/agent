"""Log Agent for monitoring runtime logs and extracting error information."""

import asyncio
import time
import re
import sys
import traceback
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from io import StringIO

from ..models.error_models import ErrorContext, ErrorType, ErrorSeverity
from ..models.mcp_models import MCPRequest, MCPResponse, ErrorAnalysisRequest
from ..utils.log_utils import parse_error_log, extract_error_info
from ..mcp.client import MCPClient
from ..mcp.server import MCPServer
from .process_monitor import ProcessMonitor


class RuntimeErrorHandler(logging.Handler):
    """Custom logging handler to capture runtime errors."""
    
    def __init__(self, log_agent):
        super().__init__()
        self.log_agent = log_agent
        self.setLevel(logging.ERROR)
    
    def emit(self, record):
        try:
            # Extract error information from log record
            error_message = self.format(record)
            
            # Filter out WebSocket connection errors and other noise
            if self._should_ignore_error(error_message):
                return
            
            # Create error context
            error_context = ErrorContext(
                error_type=ErrorType.UNKNOWN,
                error_message=error_message,
                file_path=record.pathname,
                line_number=record.lineno,
                function_name=record.funcName,
                severity=ErrorSeverity.HIGH if record.levelno >= logging.ERROR else ErrorSeverity.MEDIUM,
                stack_trace=traceback.format_exc() if record.exc_info else None,
            )
            
            # Process the error asynchronously
            asyncio.create_task(self.log_agent._process_error(error_context, "runtime"))
            
        except Exception as e:
            print(f"Error in RuntimeErrorHandler: {e}")
    
    def _should_ignore_error(self, error_message: str) -> bool:
        """Check if an error should be ignored (not a real runtime error)."""
        error_lower = error_message.lower()
        
        # Ignore WebSocket connection errors
        if any(keyword in error_lower for keyword in [
            "opening handshake failed",
            "did not receive a valid http request",
            "connection closed while reading",
            "stream ends after",
            "invalidmessage",
            "websocket handshake"
        ]):
            return True
        
        # Ignore other connection-related noise
        if any(keyword in error_lower for keyword in [
            "connection refused",
            "connection timeout",
            "address already in use"
        ]):
            return True
        
        return False


class LogFileHandler(FileSystemEventHandler):
    """File system event handler for monitoring log files."""
    
    def __init__(self, log_agent, loop: asyncio.AbstractEventLoop = None):
        self.log_agent = log_agent
        self.loop = loop
    
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(('.log', '.txt', '.err')):
            try:
                if self.loop and self.loop.is_running():
                    # Schedule coroutine on the main loop from watchdog thread
                    self.loop.call_soon_threadsafe(asyncio.create_task, self.log_agent.process_log_file(event.src_path))
                else:
                    # Fallback best-effort
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(self.log_agent.process_log_file(event.src_path))
            except RuntimeError:
                pass
    
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(('.log', '.txt', '.err')):
            try:
                if self.loop and self.loop.is_running():
                    self.loop.call_soon_threadsafe(asyncio.create_task, self.log_agent.process_log_file(event.src_path))
                else:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(self.log_agent.process_log_file(event.src_path))
            except RuntimeError:
                pass


class LogAgent:
    """Agent responsible for monitoring logs and extracting error information."""
    
    def __init__(self, name: str = "log_agent"):
        self.name = name
        self.mcp_client = MCPClient(name)
        self.mcp_server = MCPServer(name, host="localhost", port=8001)
        self.observer = Observer()
        self.monitored_files: List[str] = []
        self.error_history: List[ErrorContext] = []
        self.running = False
        
        # Runtime error monitoring
        self.runtime_handler = RuntimeErrorHandler(self)
        self.original_excepthook = sys.excepthook
        
        # Process monitoring for cross-process error detection
        self.process_monitor = ProcessMonitor(self)
        
        # Register MCP handlers
        self.mcp_server.register_handler("analyze_error", self._handle_error_analysis)
        self.mcp_server.register_handler("get_log_context", self._handle_log_context)
        self.mcp_server.register_handler("ping", self._handle_ping)
        self.mcp_server.register_handler("start_runtime_monitoring", self._handle_start_runtime_monitoring)
        self.mcp_server.register_handler("stop_runtime_monitoring", self._handle_stop_runtime_monitoring)
        
        # Main event loop reference (populated on start)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    async def start(self):
        """Start the log agent."""
        self.running = True
        print(f"Log Agent {self.name} started")
        
        # Capture the running loop for thread-safe scheduling
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None
        
        # Start MCP server in background
        asyncio.create_task(self.mcp_server.start())
        
        # Start monitoring log files
        await self._start_file_monitoring()
        
        # Start runtime error monitoring
        await self._start_runtime_monitoring()
        
        # Start process monitoring
        await self.process_monitor.start()
    
    async def stop(self):
        """Stop the log agent."""
        self.running = False
        
        # Stop runtime monitoring
        await self._stop_runtime_monitoring()
        
        # Stop process monitoring
        await self.process_monitor.stop()
        
        # Stop file monitoring
        self.observer.stop()
        self.observer.join()
        
        await self.mcp_server.stop()
        await self.mcp_client.close()
        print(f"Log Agent {self.name} stopped")
    
    async def _start_runtime_monitoring(self):
        """Start monitoring runtime errors."""
        try:
            # Add custom exception hook
            sys.excepthook = self._custom_excepthook
            
            # Add logging handler to root logger
            logging.getLogger().addHandler(self.runtime_handler)
            
            print("Runtime error monitoring started")
            
        except Exception as e:
            print(f"Error starting runtime monitoring: {e}")
    
    async def _stop_runtime_monitoring(self):
        """Stop monitoring runtime errors."""
        try:
            # Restore original exception hook
            sys.excepthook = self.original_excepthook
            
            # Remove logging handler
            logging.getLogger().removeHandler(self.runtime_handler)
            
            print("Runtime error monitoring stopped")
            
        except Exception as e:
            print(f"Error stopping runtime monitoring: {e}")
    
    def _custom_excepthook(self, exc_type, exc_value, exc_traceback):
        """Custom exception hook to capture unhandled exceptions."""
        try:
            # Create error context from exception
            error_context = ErrorContext(
                error_type=self._map_exception_type(exc_type),
                error_message=str(exc_value),
                file_path=exc_traceback.tb_frame.f_code.co_filename,
                line_number=exc_traceback.tb_lineno,
                function_name=exc_traceback.tb_frame.f_code.co_name,
                severity=ErrorSeverity.HIGH,
                stack_trace=''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
            )
            
            # Process the error asynchronously
            asyncio.create_task(self._process_error(error_context, "unhandled_exception"))
            
        except Exception as e:
            print(f"Error in custom excepthook: {e}")
        
        # Call original excepthook
        self.original_excepthook(exc_type, exc_value, exc_traceback)
    
    def _map_exception_type(self, exc_type) -> ErrorType:
        """Map Python exception types to ErrorType enum."""
        type_mapping = {
            NameError: ErrorType.NAME_ERROR,
            TypeError: ErrorType.TYPE_ERROR,
            AttributeError: ErrorType.ATTRIBUTE_ERROR,
            ImportError: ErrorType.IMPORT_ERROR,
            ModuleNotFoundError: ErrorType.IMPORT_ERROR,
            FileNotFoundError: ErrorType.FILE_NOT_FOUND,
            IndexError: ErrorType.INDEX_ERROR,
            KeyError: ErrorType.KEY_ERROR,
            SyntaxError: ErrorType.SYNTAX_ERROR,
            IndentationError: ErrorType.SYNTAX_ERROR,
            ValueError: ErrorType.VALUE_ERROR,
            ZeroDivisionError: ErrorType.ZERO_DIVISION_ERROR,
        }
        
        return type_mapping.get(exc_type, ErrorType.UNKNOWN)
    
    async def _start_file_monitoring(self):
        """Start monitoring log files for changes."""
        # For now, we'll monitor common log directories
        log_directories = [
            "./tmp",
        ]
        
        for directory in log_directories:
            try:
                handler = LogFileHandler(self, loop=self._loop)
                self.observer.schedule(handler, directory, recursive=False)
                print(f"Monitoring log directory: {directory}")
            except Exception as e:
                print(f"Failed to monitor directory {directory}: {e}")
        
        self.observer.start()
    
    async def process_log_file(self, file_path: str):
        """Process a log file and extract errors."""
        try:
            print(f"Processing log file: {file_path}")
            # Read the log file
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Parse errors from the log content
            errors = parse_error_log(content)
            
            # Process each error
            for error in errors:
                await self._process_error(error, file_path)
                
        except Exception as e:
            print(f"Error processing log file {file_path}: {e}")
    
    async def _process_error(self, error: ErrorContext, source_file: str):
        """Process a single error."""
        # Add source file information
        error.additional_context["source_file"] = source_file
        
        # Add to error history
        self.error_history.append(error)
        
        # Broadcast error to other agents
        await self._broadcast_error(error)
        
        print(f"Processed error: {error.error_type} - {error.error_message}")
    
    async def _broadcast_error(self, error: ErrorContext):
        """Broadcast error to other agents via MCP."""
        try:
            error_data = {
                "error_type": error.error_type.value,
                "error_message": error.error_message,
                "file_path": error.file_path,
                "line_number": error.line_number,
                "function_name": error.function_name,
                "stack_trace": error.stack_trace,
                "severity": error.severity.value,
                "timestamp": error.timestamp.isoformat(),
                "additional_context": error.additional_context,
            }
            
            responses = await self.mcp_client.broadcast_error(error_data)
            
            for response in responses:
                if response.result:
                    print(f"Received response from {response.source_agent}: {len(response.result.get('suggestions', []))} suggestions")
                    
        except Exception as e:
            print(f"Error broadcasting error: {e}")
    
    async def _handle_error_analysis(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle error analysis request from other agents."""
        try:
            # Extract error context from request
            error_context = request.params.get("error_context", {})
            
            # Find similar errors in history
            similar_errors = self._find_similar_errors(error_context)
            
            # Analyze the error
            analysis = await self._analyze_error(error_context, similar_errors)
            
            # Generate fix suggestions
            suggestions = self._generate_fix_suggestions(error_context, similar_errors)
            
            return {
                "analysis": analysis,
                "suggestions": suggestions,
                "confidence": 0.8,
                "processing_time": 0.1,
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _handle_log_context(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle log context request from other agents."""
        try:
            # Return recent error history
            recent_errors = self.error_history[-10:]  # Last 10 errors
            
            return {
                "recent_errors": [error.model_dump() for error in recent_errors],
                "total_errors": len(self.error_history),
                "error_types": self._get_error_type_distribution(),
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _handle_ping(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle ping request for health checks."""
        try:
            return {
                "status": "ok",
                "agent": self.name,
                "running": self.running,
                "timestamp": time.time(),
                "error_count": len(self.error_history),
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _handle_start_runtime_monitoring(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle start runtime monitoring request."""
        try:
            await self._start_runtime_monitoring()
            return {
                "status": "ok",
                "message": "Runtime monitoring started",
                "timestamp": time.time(),
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _handle_stop_runtime_monitoring(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle stop runtime monitoring request."""
        try:
            await self._stop_runtime_monitoring()
            return {
                "status": "ok",
                "message": "Runtime monitoring stopped",
                "timestamp": time.time(),
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _find_similar_errors(self, error_context: Dict[str, Any]) -> List[ErrorContext]:
        """Find similar errors in the error history."""
        similar_errors = []
        target_error_type = error_context.get("error_type")
        target_message = error_context.get("error_message", "").lower()
        
        for error in self.error_history:
            # Check if error types match
            if error.error_type.value == target_error_type:
                # Check if error messages are similar
                if target_message in error.error_message.lower() or error.error_message.lower() in target_message:
                    similar_errors.append(error)
        
        return similar_errors
    
    async def _analyze_error(self, error_context: Dict[str, Any], similar_errors: List[ErrorContext]) -> Dict[str, Any]:
        """Analyze an error and provide insights."""
        analysis = {
            "error_frequency": len(similar_errors),
            "first_occurrence": None,
            "last_occurrence": None,
            "common_patterns": [],
            "suggestions": [],
        }
        
        if similar_errors:
            # Find first and last occurrence
            timestamps = [error.timestamp for error in similar_errors]
            analysis["first_occurrence"] = min(timestamps).isoformat()
            analysis["last_occurrence"] = max(timestamps).isoformat()
            
            # Find common patterns
            analysis["common_patterns"] = self._extract_common_patterns(similar_errors)
            
            # Generate suggestions based on patterns
            analysis["suggestions"] = self._generate_suggestions(similar_errors, error_context)
        
        return analysis
    
    def _extract_common_patterns(self, errors: List[ErrorContext]) -> List[str]:
        """Extract common patterns from similar errors."""
        patterns = []
        
        # Check for common file paths
        file_paths = [error.file_path for error in errors if error.file_path]
        if file_paths:
            common_files = set(file_paths)
            if len(common_files) < len(file_paths):
                patterns.append(f"Error occurs in {len(common_files)} different files")
        
        # Check for common function names
        function_names = [error.function_name for error in errors if error.function_name]
        if function_names:
            common_functions = set(function_names)
            if len(common_functions) < len(function_names):
                patterns.append(f"Error occurs in {len(common_functions)} different functions")
        
        return patterns
    
    def _generate_suggestions(self, errors: List[ErrorContext], current_error: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate suggestions based on error patterns."""
        suggestions = []
        
        # Get error type and message
        error_type = current_error.get("error_type", "unknown")
        error_message = current_error.get("error_message", "")
        
        # Generate specific suggestions based on error type
        if error_type == "name_error":
            suggestions.append({
                "title": "Define Variable",
                "description": f"Variable '{self._extract_variable_name(error_message)}' is not defined",
                "code_snippet": f"# Define the variable before using it\n{self._extract_variable_name(error_message)} = some_value",
                "confidence_score": 0.9,
                "agent_source": self.name,
                "explanation": "Variables must be defined before they can be used"
            })
        
        elif error_type == "type_error":
            if "object is not callable" in error_message.lower():
                suggestions.append({
                    "title": "Fix Function Call",
                    "description": "You're trying to call an object that is not a function",
                    "code_snippet": "# Check if the object is callable\nif callable(my_variable):\n    result = my_variable()",
                    "confidence_score": 0.8,
                    "agent_source": self.name,
                    "explanation": "Only functions and classes can be called"
                })
            else:
                suggestions.append({
                    "title": "Check Variable Types",
                    "description": "Verify that variables have the correct types",
                    "code_snippet": "# Check variable types\nprint(type(my_variable))",
                    "confidence_score": 0.7,
                    "agent_source": self.name,
                    "explanation": "Type errors occur when operations are performed on incompatible types"
                })
        
        elif error_type == "import_error" or error_type == "module_not_found":
            module_name = self._extract_module_name(error_message)
            if module_name:
                suggestions.append({
                    "title": "Install Missing Module",
                    "description": f"Install the missing module: {module_name}",
                    "code_snippet": f"pip install {module_name}",
                    "confidence_score": 0.95,
                    "agent_source": self.name,
                    "explanation": f"The module '{module_name}' is not installed in your environment"
                })
            else:
                suggestions.append({
                    "title": "Check Import Statement",
                    "description": "Verify the import statement is correct",
                    "code_snippet": "# Check your import statement\nimport module_name",
                    "confidence_score": 0.7,
                    "agent_source": self.name,
                    "explanation": "Import errors occur when modules cannot be found or imported"
                })
        
        elif error_type == "syntax_error":
            suggestions.append({
                "title": "Fix Syntax Error",
                "description": "Check for syntax issues like missing parentheses, brackets, or quotes",
                "code_snippet": "# Review the syntax around the error line",
                "confidence_score": 0.8,
                "agent_source": self.name,
                "explanation": "Syntax errors occur when Python cannot parse your code"
            })
        
        elif error_type == "attribute_error":
            suggestions.append({
                "title": "Check Object Attributes",
                "description": "Verify the object has the required attribute",
                "code_snippet": "# Check available attributes\nprint(dir(my_object))",
                "confidence_score": 0.8,
                "agent_source": self.name,
                "explanation": "Attribute errors occur when trying to access non-existent attributes"
            })
        
        # Add frequency-based suggestions
        if len(errors) > 5:
            suggestions.append({
                "title": "High Frequency Error",
                "description": f"This error has occurred {len(errors)} times",
                "code_snippet": "# This is a recurring issue that needs attention",
                "confidence_score": 0.6,
                "agent_source": self.name,
                "explanation": "Frequent errors indicate a systematic issue that should be addressed"
            })
        
        return suggestions[:3]  # Return top 3 suggestions
    
    def _extract_variable_name(self, error_message: str) -> str:
        """Extract variable name from NameError message."""
        match = re.search(r"name '([^']+)' is not defined", error_message)
        return match.group(1) if match else "variable_name"
    
    def _extract_module_name(self, error_message: str) -> str:
        """Extract module name from ImportError message."""
        match = re.search(r"No module named '([^']+)'", error_message)
        return match.group(1) if match else "module_name"
    
    def _get_error_type_distribution(self) -> Dict[str, int]:
        """Get distribution of error types in history."""
        distribution = {}
        for error in self.error_history:
            error_type = error.error_type.value
            distribution[error_type] = distribution.get(error_type, 0) + 1
        return distribution
    
    async def connect_to_agent(self, agent_name: str, connection_info: Dict[str, Any]):
        """Connect to another agent."""
        return await self.mcp_client.connect_to_agent(agent_name, connection_info)
    
    def get_error_history(self) -> List[ErrorContext]:
        """Get the error history."""
        return self.error_history.copy()
    
    def get_recent_errors(self, count: int = 10) -> List[ErrorContext]:
        """Get recent errors."""
        return self.error_history[-count:] 

    def _generate_fix_suggestions(self, error_context: Dict[str, Any], similar_errors: List[ErrorContext]) -> List[Dict[str, Any]]:
        """Generate fix suggestions based on error context and similar errors."""
        suggestions = []
        
        # Get error type and message
        error_type = error_context.get("error_type", "unknown")
        error_message = error_context.get("error_message", "")
        
        # Generate suggestions based on error type
        if error_type == "NAME_ERROR":
            suggestions.extend(self._generate_name_error_suggestions(error_message))
        elif error_type == "IMPORT_ERROR":
            suggestions.extend(self._generate_import_error_suggestions(error_message))
        elif error_type == "ATTRIBUTE_ERROR":
            suggestions.extend(self._generate_attribute_error_suggestions(error_message))
        elif error_type == "TYPE_ERROR":
            suggestions.extend(self._generate_type_error_suggestions(error_message))
        elif error_type == "INDEX_ERROR":
            suggestions.extend(self._generate_index_error_suggestions(error_message))
        elif error_type == "KEY_ERROR":
            suggestions.extend(self._generate_key_error_suggestions(error_message))
        elif error_type == "FILE_NOT_FOUND":
            suggestions.extend(self._generate_file_not_found_suggestions(error_message))
        
        # Add suggestions based on similar errors
        if similar_errors:
            suggestions.extend(self._generate_similar_error_suggestions(similar_errors))
        
        return suggestions
    
    def _generate_name_error_suggestions(self, error_message: str) -> List[Dict[str, Any]]:
        """Generate suggestions for NameError."""
        suggestions = []
        
        # Extract variable name from error message
        import re
        match = re.search(r"name '([^']+)' is not defined", error_message)
        if match:
            var_name = match.group(1)
            suggestions.append({
                "title": f"Define variable '{var_name}'",
                "description": f"The variable '{var_name}' is used but not defined",
                "code_snippet": f"{var_name} = None  # Define the variable with appropriate value",
                "confidence_score": 0.9,
                "agent_source": self.name,
                "explanation": f"Variable '{var_name}' needs to be defined before it can be used"
            })
            
            # Check if it might be a typo
            suggestions.append({
                "title": f"Check for typos in '{var_name}'",
                "description": f"The variable name '{var_name}' might be misspelled",
                "code_snippet": f"# Check if you meant: {var_name}_corrected",
                "confidence_score": 0.7,
                "agent_source": self.name,
                "explanation": "Variable names are case-sensitive and must match exactly"
            })
        
        return suggestions
    
    def _generate_import_error_suggestions(self, error_message: str) -> List[Dict[str, Any]]:
        """Generate suggestions for ImportError."""
        suggestions = []
        
        # Extract module name from error message
        import re
        match = re.search(r"No module named '([^']+)'", error_message)
        if match:
            module_name = match.group(1)
            suggestions.append({
                "title": f"Install missing module '{module_name}'",
                "description": f"The module '{module_name}' is not installed",
                "code_snippet": f"pip install {module_name}",
                "confidence_score": 0.9,
                "agent_source": self.name,
                "explanation": f"Module '{module_name}' needs to be installed using pip"
            })
        
        match = re.search(r"cannot import name '([^']+)'", error_message)
        if match:
            import_name = match.group(1)
            suggestions.append({
                "title": f"Check import for '{import_name}'",
                "description": f"The name '{import_name}' cannot be imported",
                "code_snippet": f"# Check if '{import_name}' exists in the module",
                "confidence_score": 0.8,
                "agent_source": self.name,
                "explanation": f"Verify that '{import_name}' is available in the module being imported"
            })
        
        return suggestions
    
    def _generate_attribute_error_suggestions(self, error_message: str) -> List[Dict[str, Any]]:
        """Generate suggestions for AttributeError."""
        suggestions = []
        
        # Extract object and attribute from error message
        import re
        match = re.search(r"'([^']+)' object has no attribute '([^']+)'", error_message)
        if match:
            object_type = match.group(1)
            attribute = match.group(2)
            suggestions.append({
                "title": f"Check available attributes for {object_type}",
                "description": f"The {object_type} object doesn't have attribute '{attribute}'",
                "code_snippet": f"dir({object_type}_instance)  # Check available attributes",
                "confidence_score": 0.8,
                "agent_source": self.name,
                "explanation": f"Use dir() to see what attributes are available on {object_type} objects"
            })
        
        return suggestions
    
    def _generate_type_error_suggestions(self, error_message: str) -> List[Dict[str, Any]]:
        """Generate suggestions for TypeError."""
        suggestions = []
        
        suggestions.append({
            "title": "Check argument types",
            "description": "The function received arguments of incorrect types",
            "code_snippet": "# Check the expected types for function arguments",
            "confidence_score": 0.7,
            "agent_source": self.name,
            "explanation": "Verify that all arguments match the expected types"
        })
        
        return suggestions
    
    def _generate_index_error_suggestions(self, error_message: str) -> List[Dict[str, Any]]:
        """Generate suggestions for IndexError."""
        suggestions = []
        
        suggestions.append({
            "title": "Check list length before indexing",
            "description": "The list index is out of range",
            "code_snippet": "if len(my_list) > index:\n    value = my_list[index]",
            "confidence_score": 0.8,
            "agent_source": self.name,
            "explanation": "Always check the length of a list before accessing by index"
        })
        
        return suggestions
    
    def _generate_key_error_suggestions(self, error_message: str) -> List[Dict[str, Any]]:
        """Generate suggestions for KeyError."""
        suggestions = []
        
        suggestions.append({
            "title": "Use .get() method for safe access",
            "description": "The dictionary key doesn't exist",
            "code_snippet": "value = my_dict.get('key', default_value)",
            "confidence_score": 0.8,
            "agent_source": self.name,
            "explanation": "Use .get() method to safely access dictionary keys with a default value"
        })
        
        return suggestions
    
    def _generate_file_not_found_suggestions(self, error_message: str) -> List[Dict[str, Any]]:
        """Generate suggestions for FileNotFoundError."""
        suggestions = []
        
        suggestions.append({
            "title": "Check file path",
            "description": "The file path is incorrect or file doesn't exist",
            "code_snippet": "import os\nif os.path.exists(file_path):\n    # File exists",
            "confidence_score": 0.9,
            "agent_source": self.name,
            "explanation": "Verify the file path and check if the file exists"
        })
        
        return suggestions
    
    def _generate_similar_error_suggestions(self, similar_errors: List[ErrorContext]) -> List[Dict[str, Any]]:
        """Generate suggestions based on similar errors in history."""
        suggestions = []
        
        # Find most common patterns
        error_types = {}
        for error in similar_errors:
            error_type = error.error_type.value
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        # Suggest based on frequency
        for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
            if count > 1:
                suggestions.append({
                    "title": f"Recurring {error_type} pattern",
                    "description": f"This {error_type} has occurred {count} times",
                    "code_snippet": f"# Consider implementing a fix for {error_type}",
                    "confidence_score": 0.6,
                    "agent_source": self.name,
                    "explanation": f"This error type appears frequently, suggesting a systematic issue"
                })
        
        return suggestions 