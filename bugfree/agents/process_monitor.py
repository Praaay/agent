"""Process monitor for detecting Python errors from any process."""

import asyncio
import subprocess
import sys
import os
import re
from typing import List, Optional
from datetime import datetime

from ..models.error_models import ErrorContext, ErrorType, ErrorSeverity


class ProcessMonitor:
    """Monitor Python processes for errors."""
    
    def __init__(self, log_agent):
        self.log_agent = log_agent
        self.running = False
        self.monitored_processes = set()
        
    async def start(self):
        """Start monitoring Python processes."""
        self.running = True
        print("Process monitoring started")
        
        # Start monitoring in background
        asyncio.create_task(self._monitor_python_processes())
    
    async def stop(self):
        """Stop monitoring."""
        self.running = False
        print("Process monitoring stopped")
    
    async def _monitor_python_processes(self):
        """Monitor all Python processes for errors."""
        while self.running:
            try:
                # Find all Python processes
                python_processes = await self._find_python_processes()
                
                # Monitor each process
                for process_info in python_processes:
                    if process_info['pid'] not in self.monitored_processes:
                        await self._monitor_process(process_info)
                        self.monitored_processes.add(process_info['pid'])
                
                # Clean up finished processes
                await self._cleanup_finished_processes()
                
                # Wait before next check
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"Error in process monitoring: {e}")
                await asyncio.sleep(5)
    
    async def _find_python_processes(self) -> List[dict]:
        """Find all running Python processes."""
        try:
            if sys.platform == "darwin":  # macOS
                result = subprocess.run(
                    ["ps", "-eo", "pid,command"],
                    capture_output=True,
                    text=True
                )
            else:  # Linux
                result = subprocess.run(
                    ["ps", "-eo", "pid,cmd"],
                    capture_output=True,
                    text=True
                )
            
            processes = []
            for line in result.stdout.split('\n'):
                if 'python' in line.lower() and 'run_bugfree.py' not in line:
                    # Parse process info
                    parts = line.strip().split()
                    if parts:
                        pid = int(parts[0])
                        command = ' '.join(parts[1:])
                        processes.append({
                            'pid': pid,
                            'command': command
                        })
            
            return processes
            
        except Exception as e:
            print(f"Error finding Python processes: {e}")
            return []
    
    async def _monitor_process(self, process_info: dict):
        """Monitor a specific Python process for errors."""
        try:
            # Use strace on Linux or dtrace on macOS to monitor system calls
            # For now, we'll use a simpler approach - monitor stderr
            if sys.platform == "darwin":
                # On macOS, we can use log stream to monitor Python errors
                await self._monitor_macos_logs()
            else:
                # On Linux, we can monitor /proc filesystem
                await self._monitor_linux_process(process_info)
                
        except Exception as e:
            print(f"Error monitoring process {process_info['pid']}: {e}")
    
    async def _monitor_macos_logs(self):
        """Monitor macOS system logs for Python errors."""
        try:
            # Use log stream to monitor Python errors
            cmd = [
                "log", "stream", 
                "--predicate", "process == 'python' OR process == 'python3'",
                "--level", "error"
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            while self.running:
                try:
                    line = await asyncio.wait_for(process.stdout.readline(), timeout=1.0)
                    if line:
                        line_str = line.decode().strip()
                        if self._is_python_error(line_str):
                            await self._process_error_line(line_str)
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print(f"Error reading log stream: {e}")
                    break
                    
        except Exception as e:
            print(f"Error setting up macOS log monitoring: {e}")
    
    async def _monitor_linux_process(self, process_info: dict):
        """Monitor Linux process for errors."""
        try:
            # Monitor /proc/{pid}/fd/2 (stderr) for errors
            stderr_path = f"/proc/{process_info['pid']}/fd/2"
            if os.path.exists(stderr_path):
                # This is a simplified approach - in practice you'd need more sophisticated monitoring
                pass
        except Exception as e:
            print(f"Error monitoring Linux process: {e}")
    
    def _is_python_error(self, line: str) -> bool:
        """Check if a log line contains a Python error."""
        error_patterns = [
            r"Traceback \(most recent call last\):",
            r"NameError:",
            r"TypeError:",
            r"AttributeError:",
            r"ImportError:",
            r"SyntaxError:",
            r"FileNotFoundError:",
            r"IndexError:",
            r"KeyError:",
            r"ValueError:",
            r"ZeroDivisionError:",
        ]
        
        return any(re.search(pattern, line) for pattern in error_patterns)
    
    async def _process_error_line(self, error_line: str):
        """Process an error line from system logs."""
        try:
            # Create error context from log line
            error_context = ErrorContext(
                error_type=self._extract_error_type(error_line),
                error_message=error_line,
                file_path="unknown",
                line_number=1,
                severity=ErrorSeverity.HIGH,
                timestamp=datetime.now().isoformat(),
            )
            
            # Send to log agent for processing
            await self.log_agent._process_error(error_context, "process_monitor")
            
        except Exception as e:
            print(f"Error processing error line: {e}")
    
    def _extract_error_type(self, error_line: str) -> ErrorType:
        """Extract error type from error line."""
        error_line_lower = error_line.lower()
        
        if "nameerror" in error_line_lower:
            return ErrorType.NAME_ERROR
        elif "typeerror" in error_line_lower:
            return ErrorType.TYPE_ERROR
        elif "attributeerror" in error_line_lower:
            return ErrorType.ATTRIBUTE_ERROR
        elif "importerror" in error_line_lower:
            return ErrorType.IMPORT_ERROR
        elif "syntaxerror" in error_line_lower:
            return ErrorType.SYNTAX_ERROR
        elif "filenotfounderror" in error_line_lower:
            return ErrorType.FILE_NOT_FOUND
        elif "indexerror" in error_line_lower:
            return ErrorType.INDEX_ERROR
        elif "keyerror" in error_line_lower:
            return ErrorType.KEY_ERROR
        elif "valueerror" in error_line_lower:
            return ErrorType.VALUE_ERROR
        elif "zerodivisionerror" in error_line_lower:
            return ErrorType.ZERO_DIVISION_ERROR
        else:
            return ErrorType.UNKNOWN
    
    async def _cleanup_finished_processes(self):
        """Remove finished processes from monitoring."""
        finished_pids = set()
        
        for pid in self.monitored_processes:
            try:
                # Check if process still exists
                os.kill(pid, 0)
            except OSError:
                # Process no longer exists
                finished_pids.add(pid)
        
        # Remove finished processes
        self.monitored_processes -= finished_pids 