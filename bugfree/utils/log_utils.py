"""Log utility functions for parsing error logs and extracting error information."""

import re
import traceback
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import sys

from ..models.error_models import ErrorContext, ErrorType, ErrorSeverity


def parse_error_log(log_content: str) -> List[ErrorContext]:
    """Parse error log content and extract error contexts."""
    errors = []
    lines = log_content.split('\n')
    
    for i, line in enumerate(lines):
        error_context = extract_error_from_line(line, lines, i)
        if error_context:
            errors.append(error_context)
    
    return errors


def extract_error_from_line(line: str, all_lines: List[str], line_index: int) -> Optional[ErrorContext]:
    """Extract error information from a single log line."""
    # Python traceback patterns
    python_patterns = [
        r'Traceback \(most recent call last\):',
        r'File "(.*?)", line (\d+), in (.+)',
        r'(\w+Error): (.+)',
        r'(\w+Exception): (.+)',
    ]
    
    # JavaScript/Node.js patterns
    js_patterns = [
        r'Error: (.+)',
        r'at (.+) \((.+):(\d+):(\d+)\)',
        r'TypeError: (.+)',
        r'ReferenceError: (.+)',
        r'SyntaxError: (.+)',
    ]
    
    # Java patterns
    java_patterns = [
        r'Exception in thread "(.+)" (.+): (.+)',
        r'at (.+)\.(.+)\((.+):(\d+)\)',
        r'Caused by: (.+): (.+)',
    ]
    
    # Check for Python errors
    if any(re.search(pattern, line) for pattern in python_patterns):
        return extract_python_error(line, all_lines, line_index)
    
    # Check for JavaScript errors
    if any(re.search(pattern, line) for pattern in js_patterns):
        return extract_javascript_error(line, all_lines, line_index)
    
    # Check for Java errors
    if any(re.search(pattern, line) for pattern in java_patterns):
        return extract_java_error(line, all_lines, line_index)
    
    return None


def extract_python_error(line: str, all_lines: List[str], line_index: int) -> Optional[ErrorContext]:
    """Extract Python error information."""
    # Look for the error message
    error_match = re.search(r'(\w+Error|\w+Exception): (.+)', line)
    if not error_match:
        return None
    
    error_type_name = error_match.group(1)
    error_message = error_match.group(2)
    
    # Map error type
    error_type = map_python_error_type(error_type_name)
    
    # Look for file and line information in previous lines
    file_path = None
    line_number = None
    function_name = None
    
    for i in range(line_index - 1, max(0, line_index - 10), -1):
        file_match = re.search(r'File "(.*?)", line (\d+), in (.+)', all_lines[i])
        if file_match:
            file_path = file_match.group(1)
            line_number = int(file_match.group(2))
            function_name = file_match.group(3)
            break
    
    # Extract stack trace
    stack_trace = extract_stack_trace(all_lines, line_index)
    
    return ErrorContext(
        error_type=error_type,
        error_message=error_message,
        file_path=file_path,
        line_number=line_number,
        function_name=function_name,
        stack_trace=stack_trace,
        severity=determine_severity(error_type, error_message),
    )


def extract_javascript_error(line: str, all_lines: List[str], line_index: int) -> Optional[ErrorContext]:
    """Extract JavaScript error information."""
    # Look for error message
    error_match = re.search(r'(\w+Error): (.+)', line)
    if not error_match:
        return None
    
    error_type_name = error_match.group(1)
    error_message = error_match.group(2)
    
    # Map error type
    error_type = map_javascript_error_type(error_type_name)
    
    # Look for stack trace information
    file_path = None
    line_number = None
    function_name = None
    
    for i in range(line_index + 1, min(len(all_lines), line_index + 10)):
        stack_match = re.search(r'at (.+) \((.+):(\d+):(\d+)\)', all_lines[i])
        if stack_match:
            function_name = stack_match.group(1)
            file_path = stack_match.group(2)
            line_number = int(stack_match.group(3))
            break
    
    return ErrorContext(
        error_type=error_type,
        error_message=error_message,
        file_path=file_path,
        line_number=line_number,
        function_name=function_name,
        severity=determine_severity(error_type, error_message),
    )


def extract_java_error(line: str, all_lines: List[str], line_index: int) -> Optional[ErrorContext]:
    """Extract Java error information."""
    # Look for exception message
    exception_match = re.search(r'Exception in thread "(.+)" (.+): (.+)', line)
    if not exception_match:
        return None
    
    thread_name = exception_match.group(1)
    exception_type = exception_match.group(2)
    error_message = exception_match.group(3)
    
    # Map error type
    error_type = map_java_error_type(exception_type)
    
    # Look for stack trace information
    file_path = None
    line_number = None
    function_name = None
    
    for i in range(line_index + 1, min(len(all_lines), line_index + 10)):
        stack_match = re.search(r'at (.+)\.(.+)\((.+):(\d+)\)', all_lines[i])
        if stack_match:
            class_name = stack_match.group(1)
            function_name = stack_match.group(2)
            file_path = stack_match.group(3)
            line_number = int(stack_match.group(4))
            break
    
    return ErrorContext(
        error_type=error_type,
        error_message=error_message,
        file_path=file_path,
        line_number=line_number,
        function_name=function_name,
        severity=determine_severity(error_type, error_message),
    )


def extract_stack_trace(all_lines: List[str], error_line_index: int) -> Optional[str]:
    """Extract the full stack trace."""
    stack_trace_lines = []
    
    # Look backwards for the start of the traceback
    start_index = error_line_index
    for i in range(error_line_index - 1, max(0, error_line_index - 20), -1):
        if "Traceback (most recent call last):" in all_lines[i]:
            start_index = i
            break
    
    # Collect stack trace lines
    for i in range(start_index, min(len(all_lines), error_line_index + 5)):
        line = all_lines[i].strip()
        if line:
            stack_trace_lines.append(line)
        elif stack_trace_lines and not line:
            break
    
    return '\n'.join(stack_trace_lines) if stack_trace_lines else None


def map_python_error_type(error_type_name: str) -> ErrorType:
    """Map Python error type names to ErrorType enum."""
    error_mapping = {
        'SyntaxError': ErrorType.SYNTAX_ERROR,
        'TypeError': ErrorType.TYPE_ERROR,
        'AttributeError': ErrorType.ATTRIBUTE_ERROR,
        'IndexError': ErrorType.INDEX_ERROR,
        'KeyError': ErrorType.KEY_ERROR,
        'ValueError': ErrorType.VALUE_ERROR,
        'FileNotFoundError': ErrorType.FILE_NOT_FOUND,
        'PermissionError': ErrorType.PERMISSION_ERROR,
        'ImportError': ErrorType.IMPORT_ERROR,
        'ModuleNotFoundError': ErrorType.IMPORT_ERROR,
        'TimeoutError': ErrorType.TIMEOUT_ERROR,
        'ConnectionError': ErrorType.CONNECTION_ERROR,
    }
    
    return error_mapping.get(error_type_name, ErrorType.UNKNOWN)


def map_javascript_error_type(error_type_name: str) -> ErrorType:
    """Map JavaScript error type names to ErrorType enum."""
    error_mapping = {
        'TypeError': ErrorType.TYPE_ERROR,
        'ReferenceError': ErrorType.ATTRIBUTE_ERROR,
        'SyntaxError': ErrorType.SYNTAX_ERROR,
        'RangeError': ErrorType.VALUE_ERROR,
        'URIError': ErrorType.VALUE_ERROR,
        'EvalError': ErrorType.SYNTAX_ERROR,
    }
    
    return error_mapping.get(error_type_name, ErrorType.UNKNOWN)


def map_java_error_type(exception_type: str) -> ErrorType:
    """Map Java exception type names to ErrorType enum."""
    error_mapping = {
        'NullPointerException': ErrorType.ATTRIBUTE_ERROR,
        'ArrayIndexOutOfBoundsException': ErrorType.INDEX_ERROR,
        'ClassCastException': ErrorType.TYPE_ERROR,
        'IllegalArgumentException': ErrorType.VALUE_ERROR,
        'FileNotFoundException': ErrorType.FILE_NOT_FOUND,
        'IOException': ErrorType.FILE_NOT_FOUND,
        'SecurityException': ErrorType.PERMISSION_ERROR,
        'TimeoutException': ErrorType.TIMEOUT_ERROR,
    }
    
    return error_mapping.get(exception_type, ErrorType.UNKNOWN)


def determine_severity(error_type: ErrorType, error_message: str) -> ErrorSeverity:
    """Determine error severity based on type and message."""
    # Critical errors
    if error_type in [ErrorType.SYNTAX_ERROR, ErrorType.IMPORT_ERROR]:
        return ErrorSeverity.CRITICAL
    
    # High severity errors
    if error_type in [ErrorType.FILE_NOT_FOUND, ErrorType.PERMISSION_ERROR]:
        return ErrorSeverity.HIGH
    
    # Medium severity errors (default)
    if error_type in [ErrorType.TYPE_ERROR, ErrorType.ATTRIBUTE_ERROR, ErrorType.INDEX_ERROR, ErrorType.KEY_ERROR]:
        return ErrorSeverity.MEDIUM
    
    # Low severity errors
    if error_type in [ErrorType.VALUE_ERROR, ErrorType.TIMEOUT_ERROR, ErrorType.CONNECTION_ERROR]:
        return ErrorSeverity.LOW
    
    return ErrorSeverity.MEDIUM


def extract_error_info(exception: Exception, traceback_obj: Optional[traceback] = None) -> ErrorContext:
    """Extract error information from a Python exception."""
    if traceback_obj is None:
        traceback_obj = traceback
    
    exc_type, exc_value, exc_traceback = sys.exc_info()
    
    # Get the error message
    error_message = str(exc_value)
    
    # Get the error type
    error_type_name = exc_type.__name__ if exc_type else "Exception"
    error_type = map_python_error_type(error_type_name)
    
    # Extract file and line information from traceback
    file_path = None
    line_number = None
    function_name = None
    
    if exc_traceback:
        frame = exc_traceback.tb_frame
        while frame.f_back:
            frame = frame.f_back
        
        code = frame.f_code
        file_path = code.co_filename
        line_number = frame.f_lineno
        function_name = code.co_name
    
    # Get stack trace
    stack_trace = ''.join(traceback_obj.format_exception(exc_type, exc_value, exc_traceback))
    
    return ErrorContext(
        error_type=error_type,
        error_message=error_message,
        file_path=file_path,
        line_number=line_number,
        function_name=function_name,
        stack_trace=stack_trace,
        severity=determine_severity(error_type, error_message),
    ) 