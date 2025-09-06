"""Code Agent for reading codebase context and suggesting fixes."""

import asyncio
import ast
import re
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import time

from ..models.error_models import ErrorContext, FixSuggestion, ErrorType
from ..models.mcp_models import MCPRequest, MCPResponse, CodeContextRequest
from ..utils.file_utils import read_file_content_sync, get_surrounding_lines, get_file_language
from ..mcp.client import MCPClient
from ..mcp.server import MCPServer


class CodeAgent:
    """Agent responsible for reading codebase context and suggesting fixes."""
    
    def __init__(self, name: str = "code_agent"):
        self.name = name
        self.mcp_client = MCPClient(name)
        self.mcp_server = MCPServer(name, host="localhost", port=8002)
        self.project_root: Optional[str] = None
        self.code_cache: Dict[str, str] = {}
        self.fix_patterns: Dict[str, List[Dict[str, Any]]] = {}
        self.running = False
        
        # Register MCP handlers
        self.mcp_server.register_handler("analyze_error", self._handle_error_analysis)
        self.mcp_server.register_handler("get_code_context", self._handle_code_context)
        self.mcp_server.register_handler("suggest_fixes", self._handle_suggest_fixes)
        self.mcp_server.register_handler("ping", self._handle_ping)
        
        # Initialize fix patterns
        self._initialize_fix_patterns()
    
    def _initialize_fix_patterns(self):
        """Initialize common fix patterns for different error types."""
        self.fix_patterns = {
            "syntax_error": [
                {
                    "pattern": r"SyntaxError: invalid syntax",
                    "suggestions": [
                        "Check for missing parentheses, brackets, or quotes",
                        "Verify proper indentation",
                        "Check for incomplete statements",
                    ]
                },
                {
                    "pattern": r"IndentationError",
                    "suggestions": [
                        "Fix indentation - use consistent spaces or tabs",
                        "Check for mixed tabs and spaces",
                        "Ensure proper code block structure",
                    ]
                }
            ],
            "type_error": [
                {
                    "pattern": r"TypeError: .* object is not callable",
                    "suggestions": [
                        "Check if you're calling a variable instead of a function",
                        "Verify the object type before calling",
                        "Use proper function names",
                    ]
                },
                {
                    "pattern": r"TypeError: .* object is not iterable",
                    "suggestions": [
                        "Check if the object supports iteration",
                        "Use list(), tuple(), or dict() to convert",
                        "Verify the object type",
                    ]
                }
            ],
            "attribute_error": [
                {
                    "pattern": r"AttributeError: .* object has no attribute",
                    "suggestions": [
                        "Check if the attribute name is correct",
                        "Verify the object type and available attributes",
                        "Use dir() to see available attributes",
                    ]
                }
            ],
            "import_error": [
                {
                    "pattern": r"ModuleNotFoundError: No module named",
                    "suggestions": [
                        "Install the missing module: pip install <module_name>",
                        "Check if the module name is spelled correctly",
                        "Verify the module is in your Python path",
                    ]
                },
                {
                    "pattern": r"ImportError: cannot import name",
                    "suggestions": [
                        "Check if the import name is correct",
                        "Verify the module structure",
                        "Check for circular imports",
                    ]
                }
            ],
            "file_not_found": [
                {
                    "pattern": r"FileNotFoundError",
                    "suggestions": [
                        "Check if the file path is correct",
                        "Verify the file exists in the specified location",
                        "Use absolute paths or check relative path",
                    ]
                }
            ],
            "index_error": [
                {
                    "pattern": r"IndexError: list index out of range",
                    "suggestions": [
                        "Check the list length before accessing by index",
                        "Use len() to verify the list size",
                        "Consider using try-except for safe access",
                    ]
                }
            ],
            "key_error": [
                {
                    "pattern": r"KeyError",
                    "suggestions": [
                        "Check if the key exists in the dictionary",
                        "Use .get() method for safe access",
                        "Verify the key name and type",
                    ]
                }
            ],
        }
    
    async def start(self):
        """Start the code agent."""
        self.running = True
        print(f"Code Agent {self.name} started")
        
        # Start MCP server in background
        asyncio.create_task(self.mcp_server.start())
    
    async def stop(self):
        """Stop the code agent."""
        self.running = False
        await self.mcp_server.stop()
        await self.mcp_client.close()
        print(f"Code Agent {self.name} stopped")
    
    async def _handle_error_analysis(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle error analysis request from other agents."""
        try:
            error_context = request.params.get("error_context", {})
            file_path = error_context.get("file_path")
            line_number = error_context.get("line_number")
            
            if file_path and line_number:
                suggestions = await self._analyze_code_error(file_path, line_number, error_context)
            else:
                suggestions = await self._analyze_general_error(error_context)
            
            return {
                "suggestions": suggestions,
                "confidence": 0.8,
                "processing_time": 0.1,
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _handle_code_context(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle code context request from other agents."""
        try:
            file_path = request.params.get("file_path")
            line_number = request.params.get("line_number")
            context_lines = request.params.get("context_lines", 10)
            
            if not file_path:
                return {"error": "file_path is required"}
            
            context = await self._get_code_context(file_path, line_number, context_lines)
            return context
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _handle_suggest_fixes(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle fix suggestions request from other agents."""
        try:
            error_context = request.params.get("error_context", {})
            suggestions = await self._generate_comprehensive_fix_suggestions(error_context)
            
            return {
                "suggestions": suggestions,
                "confidence": 0.8,
                "processing_time": 0.2,
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
                "code_cache_size": len(self.code_cache),
                "fix_patterns_count": len(self.fix_patterns),
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _analyze_code_error(self, file_path: str, line_number: int, error_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze a specific code error at a given line."""
        suggestions = []
        
        try:
            # Get the code context around the error
            surrounding_code = get_surrounding_lines(file_path, line_number, 5)
            if not surrounding_code:
                return suggestions
            
            # Get the specific line that caused the error
            lines = surrounding_code.split('\n')
            error_line = lines[min(line_number - 1, len(lines) - 1)]
            
            # Analyze based on error type
            error_type = error_context.get("error_type", "unknown")
            error_message = error_context.get("error_message", "")
            
            # Generate specific suggestions based on error type and code context
            specific_suggestions = self._generate_specific_suggestions(
                error_type, error_message, error_line, surrounding_code
            )
            
            suggestions.extend(specific_suggestions)
            
        except Exception as e:
            print(f"Error analyzing code error: {e}")
        
        return suggestions
    
    async def _analyze_general_error(self, error_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze a general error without specific code context."""
        error_type = error_context.get("error_type", "unknown")
        error_message = error_context.get("error_message", "")
        
        suggestions = []
        
        # Get general suggestions based on error type
        if error_type in self.fix_patterns:
            for pattern_info in self.fix_patterns[error_type]:
                if re.search(pattern_info["pattern"], error_message, re.IGNORECASE):
                    for suggestion_text in pattern_info["suggestions"]:
                        suggestions.append({
                            "title": f"Fix {error_type.replace('_', ' ').title()}",
                            "description": suggestion_text,
                            "code_snippet": f"# {suggestion_text}",
                            "confidence_score": 0.6,
                            "agent_source": self.name,
                        })
        
        return suggestions
    
    async def _get_code_context(self, file_path: str, line_number: Optional[int] = None, context_lines: int = 10) -> Dict[str, Any]:
        """Get code context for a specific file and line."""
        try:
            # Read file content
            file_content = read_file_content_sync(file_path)
            if not file_content:
                return {"error": "Could not read file"}
            
            # Get language
            language = get_file_language(file_path)
            
            # Get surrounding code if line number is provided
            surrounding_code = ""
            if line_number:
                surrounding_code = get_surrounding_lines(file_path, line_number, context_lines) or ""
            
            # Extract imports (for Python files)
            imports = []
            if language == "python":
                imports = self._extract_python_imports(file_content)
            
            # Extract function/class context
            function_context = None
            class_context = None
            if line_number and language == "python":
                function_context, class_context = self._extract_python_context(file_content, line_number)
            
            return {
                "file_content": file_content,
                "surrounding_code": surrounding_code,
                "imports": imports,
                "function_context": function_context,
                "class_context": class_context,
                "language": language,
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _extract_python_imports(self, code: str) -> List[str]:
        """Extract import statements from Python code."""
        imports = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(f"import {alias.name}")
                    else:
                        module = node.module or ""
                        names = [alias.name for alias in node.names]
                        imports.append(f"from {module} import {', '.join(names)}")
        except SyntaxError:
            # If the code has syntax errors, try to extract imports with regex
            import_pattern = r'^(?:from\s+(\w+(?:\.\w+)*)\s+import\s+(.+)|import\s+(.+))'
            for line in code.split('\n'):
                match = re.match(import_pattern, line.strip())
                if match:
                    imports.append(line.strip())
        
        return imports
    
    def _extract_python_context(self, code: str, line_number: int) -> Tuple[Optional[str], Optional[str]]:
        """Extract function and class context for a specific line."""
        function_context = None
        class_context = None
        
        try:
            tree = ast.parse(code)
            lines = code.split('\n')
            
            for node in ast.walk(tree):
                if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                    if node.lineno <= line_number <= node.end_lineno:
                        if isinstance(node, ast.FunctionDef):
                            function_context = f"def {node.name}(...)"
                        elif isinstance(node, ast.ClassDef):
                            class_context = f"class {node.name}"
                        elif isinstance(node, ast.AsyncFunctionDef):
                            function_context = f"async def {node.name}(...)"
            
        except SyntaxError:
            # If there are syntax errors, try to extract context with regex
            pass
        
        return function_context, class_context
    
    def _generate_specific_suggestions(self, error_type: str, error_message: str, error_line: str, surrounding_code: str) -> List[Dict[str, Any]]:
        """Generate specific suggestions based on error type and code context."""
        suggestions = []
        
        # Common Python-specific suggestions
        if error_type == "syntax_error":
            if "invalid syntax" in error_message.lower():
                # Check for common syntax issues
                if error_line.count('(') != error_line.count(')'):
                    suggestions.append({
                        "title": "Fix Parentheses Mismatch",
                        "description": "Check for missing or extra parentheses",
                        "code_snippet": "# Review parentheses in this line:\n" + error_line,
                        "confidence_score": 0.9,
                        "agent_source": self.name,
                    })
                
                if error_line.count('[') != error_line.count(']'):
                    suggestions.append({
                        "title": "Fix Bracket Mismatch",
                        "description": "Check for missing or extra brackets",
                        "code_snippet": "# Review brackets in this line:\n" + error_line,
                        "confidence_score": 0.9,
                        "agent_source": self.name,
                    })
        
        elif error_type == "type_error":
            if "object is not callable" in error_message:
                suggestions.append({
                    "title": "Fix Function Call",
                    "description": "The object is not callable. Check if it's a function.",
                    "code_snippet": "# Verify this is a function:\n" + error_line,
                    "confidence_score": 0.8,
                    "agent_source": self.name,
                })
        
        elif error_type == "attribute_error":
            if "object has no attribute" in error_message:
                suggestions.append({
                    "title": "Fix Attribute Access",
                    "description": "The object doesn't have the specified attribute",
                    "code_snippet": "# Check available attributes:\nprint(dir(object_name))",
                    "confidence_score": 0.7,
                    "agent_source": self.name,
                })
        
        elif error_type == "import_error" or error_type == "module_not_found":
            if "no module named" in error_message:
                module_name = re.search(r"no module named ['\"]([^'\"]+)['\"]", error_message)
                if module_name:
                    module = module_name.group(1)
                    suggestions.append({
                        "title": "Install Missing Module",
                        "description": f"Install the missing module: {module}",
                        "code_snippet": f"pip install {module}",
                        "confidence_score": 0.9,
                        "agent_source": self.name,
                    })
        
        elif error_type == "name_error":
            if "is not defined" in error_message:
                variable_name = re.search(r"name '([^']+)' is not defined", error_message)
                if variable_name:
                    var_name = variable_name.group(1)
                    suggestions.append({
                        "title": "Define Variable",
                        "description": f"Variable '{var_name}' is not defined",
                        "code_snippet": f"{var_name} = some_value  # Define the variable",
                        "confidence_score": 0.9,
                        "agent_source": self.name,
                    })
        
        return suggestions
    
    async def _generate_comprehensive_fix_suggestions(self, error_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate comprehensive fix suggestions based on error context and code analysis."""
        suggestions = []
        
        # Get error details
        error_type = error_context.get("error_type", "unknown")
        error_message = error_context.get("error_message", "")
        file_path = error_context.get("file_path")
        line_number = error_context.get("line_number")
        
        # Generate suggestions based on error type
        if error_type == "NAME_ERROR":
            suggestions.extend(await self._generate_name_error_fixes(error_context))
        elif error_type == "IMPORT_ERROR":
            suggestions.extend(await self._generate_import_error_fixes(error_context))
        elif error_type == "ATTRIBUTE_ERROR":
            suggestions.extend(await self._generate_attribute_error_fixes(error_context))
        elif error_type == "TYPE_ERROR":
            suggestions.extend(await self._generate_type_error_fixes(error_context))
        elif error_type == "INDEX_ERROR":
            suggestions.extend(await self._generate_index_error_fixes(error_context))
        elif error_type == "KEY_ERROR":
            suggestions.extend(await self._generate_key_error_fixes(error_context))
        elif error_type == "FILE_NOT_FOUND":
            suggestions.extend(await self._generate_file_not_found_fixes(error_context))
        
        # Add general suggestions based on code context
        if file_path and line_number:
            context_suggestions = await self._generate_context_based_suggestions(file_path, line_number, error_context)
            suggestions.extend(context_suggestions)
        
        return suggestions
    
    async def _generate_name_error_fixes(self, error_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate fixes for NameError based on code context."""
        suggestions = []
        
        error_message = error_context.get("error_message", "")
        file_path = error_context.get("file_path")
        line_number = error_context.get("line_number")
        
        # Extract variable name from error message
        import re
        match = re.search(r"name '([^']+)' is not defined", error_message)
        if match:
            var_name = match.group(1)
            
            # Check if it should be imported
            if file_path and line_number:
                imports = await self._get_file_imports(file_path)
                if var_name in imports:
                    suggestions.append({
                        "title": f"Import {var_name}",
                        "description": f"Variable '{var_name}' is available as an import",
                        "code_snippet": f"from {imports[var_name]} import {var_name}",
                        "confidence_score": 0.9,
                        "agent_source": self.name,
                        "explanation": f"'{var_name}' is available as an import from {imports[var_name]}"
                    })
            
            # Check if it's a common variable that should be defined
            common_vars = {
                "self": "This should be used within a class method",
                "cls": "This should be used within a class method",
                "args": "This should be defined in function parameters",
                "kwargs": "This should be defined in function parameters",
            }
            
            if var_name in common_vars:
                suggestions.append({
                    "title": f"Define {var_name} properly",
                    "description": common_vars[var_name],
                    "code_snippet": f"# {common_vars[var_name]}",
                    "confidence_score": 0.8,
                    "agent_source": self.name,
                    "explanation": f"'{var_name}' is a common variable that needs proper definition"
                })
            
            # General suggestion
            suggestions.append({
                "title": f"Define variable '{var_name}'",
                "description": f"Variable '{var_name}' needs to be defined before use",
                "code_snippet": f"{var_name} = None  # Replace with appropriate value",
                "confidence_score": 0.7,
                "agent_source": self.name,
                "explanation": f"Variable '{var_name}' must be defined before it can be used"
            })
        
        return suggestions
    
    async def _generate_import_error_fixes(self, error_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate fixes for ImportError based on code context."""
        suggestions = []
        
        error_message = error_context.get("error_message", "")
        
        # Extract module name from error message
        import re
        match = re.search(r"No module named '([^']+)'", error_message)
        if match:
            module_name = match.group(1)
            suggestions.append({
                "title": f"Install {module_name}",
                "description": f"Module '{module_name}' is not installed",
                "code_snippet": f"pip install {module_name}",
                "confidence_score": 0.9,
                "agent_source": self.name,
                "explanation": f"Install the missing module using pip"
            })
            
            # Check for common alternatives
            alternatives = {
                "PIL": "pillow",
                "cv2": "opencv-python",
                "yaml": "PyYAML",
            }
            
            if module_name in alternatives:
                suggestions.append({
                    "title": f"Install {alternatives[module_name]}",
                    "description": f"'{module_name}' is available as '{alternatives[module_name]}'",
                    "code_snippet": f"pip install {alternatives[module_name]}",
                    "confidence_score": 0.8,
                    "agent_source": self.name,
                    "explanation": f"'{module_name}' is the import name for '{alternatives[module_name]}' package"
                })
        
        return suggestions
    
    async def _generate_attribute_error_fixes(self, error_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate fixes for AttributeError based on code context."""
        suggestions = []
        
        error_message = error_context.get("error_message", "")
        
        # Extract object and attribute from error message
        import re
        match = re.search(r"'([^']+)' object has no attribute '([^']+)'", error_message)
        if match:
            object_type = match.group(1)
            attribute = match.group(2)
            
            suggestions.append({
                "title": f"Check {object_type} attributes",
                "description": f"'{object_type}' doesn't have attribute '{attribute}'",
                "code_snippet": f"dir({object_type}_instance)  # See available attributes",
                "confidence_score": 0.8,
                "agent_source": self.name,
                "explanation": f"Use dir() to see what attributes are available on {object_type} objects"
            })
            
            # Suggest common alternatives
            common_alternatives = {
                "list": {
                    "append": "add",
                    "length": "len",
                },
                "dict": {
                    "keys": "key",
                    "values": "value",
                },
                "str": {
                    "length": "len",
                    "upper": "uppercase",
                }
            }
            
            if object_type in common_alternatives and attribute in common_alternatives[object_type]:
                alt = common_alternatives[object_type][attribute]
                suggestions.append({
                    "title": f"Use '{alt}' instead of '{attribute}'",
                    "description": f"'{object_type}' uses '{alt}' not '{attribute}'",
                    "code_snippet": f"# Use {alt} instead of {attribute}",
                    "confidence_score": 0.7,
                    "agent_source": self.name,
                    "explanation": f"'{object_type}' objects use '{alt}' method, not '{attribute}'"
                })
        
        return suggestions
    
    async def _generate_type_error_fixes(self, error_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate fixes for TypeError based on code context."""
        suggestions = []
        
        suggestions.append({
            "title": "Check argument types",
            "description": "Function received arguments of incorrect types",
            "code_snippet": "# Verify argument types match function signature",
            "confidence_score": 0.7,
            "agent_source": self.name,
            "explanation": "Check that all arguments match the expected types for the function"
        })
        
        return suggestions
    
    async def _generate_index_error_fixes(self, error_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate fixes for IndexError based on code context."""
        suggestions = []
        
        suggestions.append({
            "title": "Check list length before indexing",
            "description": "List index is out of range",
            "code_snippet": "if len(my_list) > index:\n    value = my_list[index]\nelse:\n    # Handle empty list case",
            "confidence_score": 0.8,
            "agent_source": self.name,
            "explanation": "Always check the length of a list before accessing by index"
        })
        
        return suggestions
    
    async def _generate_key_error_fixes(self, error_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate fixes for KeyError based on code context."""
        suggestions = []
        
        suggestions.append({
            "title": "Use .get() for safe access",
            "description": "Dictionary key doesn't exist",
            "code_snippet": "value = my_dict.get('key', default_value)  # Safe access with default",
            "confidence_score": 0.8,
            "agent_source": self.name,
            "explanation": "Use .get() method to safely access dictionary keys with a default value"
        })
        
        return suggestions
    
    async def _generate_file_not_found_fixes(self, error_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate fixes for FileNotFoundError based on code context."""
        suggestions = []
        
        suggestions.append({
            "title": "Check file path",
            "description": "File path is incorrect or file doesn't exist",
            "code_snippet": "import os\nif os.path.exists(file_path):\n    # File exists\nelse:\n    # File not found",
            "confidence_score": 0.9,
            "agent_source": self.name,
            "explanation": "Verify the file path and check if the file exists before trying to open it"
        })
        
        return suggestions
    
    async def _generate_context_based_suggestions(self, file_path: str, line_number: int, error_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate suggestions based on code context around the error."""
        suggestions = []
        
        try:
            # Get surrounding code
            surrounding_code = get_surrounding_lines(file_path, line_number, 10)
            if not surrounding_code:
                return suggestions
            
            # Analyze the code context
            lines = surrounding_code.split('\n')
            error_line = lines[min(line_number - 1, len(lines) - 1)]
            
            # Check for common patterns
            if "import" in error_line.lower():
                suggestions.append({
                    "title": "Check import statement",
                    "description": "Error might be related to import",
                    "code_snippet": "# Verify import is correct and module is available",
                    "confidence_score": 0.6,
                    "agent_source": self.name,
                    "explanation": "Import statements can cause various errors if modules are missing or incorrectly named"
                })
            
            if "def " in surrounding_code or "class " in surrounding_code:
                suggestions.append({
                    "title": "Check function/class scope",
                    "description": "Error might be related to scope",
                    "code_snippet": "# Verify variables are in the correct scope",
                    "confidence_score": 0.6,
                    "agent_source": self.name,
                    "explanation": "Variables must be defined in the correct scope to be accessible"
                })
            
        except Exception as e:
            print(f"Error generating context-based suggestions: {e}")
        
        return suggestions
    
    async def _get_file_imports(self, file_path: str) -> Dict[str, str]:
        """Get imports from a file to suggest import fixes."""
        try:
            file_content = read_file_content_sync(file_path)
            if not file_content:
                return {}
            
            imports = {}
            lines = file_content.split('\n')
            
            for line in lines:
                line = line.strip()
                if line.startswith('import ') or line.startswith('from '):
                    # Parse import statements
                    if line.startswith('from '):
                        # from module import name
                        parts = line.split(' import ')
                        if len(parts) == 2:
                            module = parts[0].replace('from ', '').strip()
                            names = parts[1].strip().split(',')
                            for name in names:
                                name = name.strip()
                                imports[name] = module
                    elif line.startswith('import '):
                        # import module
                        module = line.replace('import ', '').strip()
                        imports[module] = module
            
            return imports
            
        except Exception as e:
            print(f"Error parsing imports from {file_path}: {e}")
            return {}
    
    async def connect_to_agent(self, agent_name: str, connection_info: Dict[str, Any]):
        """Connect to another agent."""
        return await self.mcp_client.connect_to_agent(agent_name, connection_info)
    
    def set_project_root(self, project_root: str):
        """Set the project root directory."""
        self.project_root = project_root
    
    def get_code_cache(self) -> Dict[str, str]:
        """Get the code cache."""
        return self.code_cache.copy()
    
    def clear_code_cache(self):
        """Clear the code cache."""
        self.code_cache.clear() 