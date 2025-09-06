#!/usr/bin/env python3
"""
Bugfree Multi-Agent Debugging System

Main entry point for the Bugfree debugging agent system.
"""

import asyncio
import sys
from typing import Optional
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.text import Text

from bugfree.core.orchestrator import OrchestratorAgent
from bugfree.agents.log_agent import LogAgent
from bugfree.agents.code_agent import CodeAgent
from bugfree.models.error_models import ErrorContext, ErrorType, ErrorSeverity
from bugfree.mcp.websocket_server import BugfreeWebSocketServer


app = typer.Typer()
console = Console()


class BugfreeSystem:
    """Main system class that manages all agents."""
    
    def __init__(self):
        self.orchestrator = OrchestratorAgent()
        self.log_agent = LogAgent()
        self.code_agent = CodeAgent()
        self.websocket_server = BugfreeWebSocketServer()
        self.websocket_task = None
        self.running = False
    
    async def start(self):
        """Start all agents in the correct order."""
        console.print("[bold blue]Starting Bugfree Multi-Agent System...[/bold blue]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            # Start Log Agent
            task1 = progress.add_task("Starting Log Agent...", total=None)
            await self.log_agent.start()
            progress.update(task1, description="Log Agent started")
            
            # Start Code Agent
            task2 = progress.add_task("Starting Code Agent...", total=None)
            await self.code_agent.start()
            progress.update(task2, description="Code Agent started")
            
                    # Start Orchestrator (this will connect to other agents)
        task3 = progress.add_task("Starting Orchestrator...", total=None)
        await self.orchestrator.start()
        progress.update(task3, description="Orchestrator started")
        
        # Start WebSocket server for VS Code extension
        task4 = progress.add_task("Starting WebSocket Server...", total=None)
        # Start WebSocket server in background and keep it running
        self.websocket_task = asyncio.create_task(self.websocket_server.start(self.orchestrator))
        progress.update(task4, description="WebSocket server started")
        
        self.running = True
        console.print("[bold green]✓ All agents started successfully![/bold green]")
    
    async def stop(self):
        """Stop all agents."""
        console.print("[bold yellow]Stopping Bugfree Multi-Agent System...[/bold yellow]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            # Stop in reverse order
            task1 = progress.add_task("Stopping WebSocket Server...", total=None)
            if self.websocket_task:
                self.websocket_task.cancel()
            await self.websocket_server.stop()
            progress.update(task1, description="WebSocket server stopped")
            
            task2 = progress.add_task("Stopping Orchestrator...", total=None)
            await self.orchestrator.stop()
            progress.update(task2, description="Orchestrator stopped")
            
            task3 = progress.add_task("Stopping Code Agent...", total=None)
            await self.code_agent.stop()
            progress.update(task3, description="Code Agent stopped")
            
            task4 = progress.add_task("Stopping Log Agent...", total=None)
            await self.log_agent.stop()
            progress.update(task4, description="Log Agent stopped")
        
        self.running = False
        console.print("[bold green]✓ All agents stopped successfully![/bold green]")
    
    async def process_error(self, error_message: str, file_path: str, line_number: int):
        """Process an error through the system."""
        if not self.running:
            console.print("[bold red]System is not running. Start it first with 'start' command.[/bold red]")
            return
        
        # Create error context
        error_context = ErrorContext(
            error_type=ErrorType.UNKNOWN,
            error_message=error_message,
            file_path=file_path,
            line_number=line_number,
            severity=ErrorSeverity.MEDIUM,
        )
        
        # Process through orchestrator
        suggestions = await self.orchestrator.process_error(error_context)
        
        # Display results
        self._display_suggestions(suggestions, error_context)
    
    def _display_suggestions(self, suggestions: list, error_context: ErrorContext):
        """Display suggestions in a nice format."""
        console.print(f"\n[bold]Error Analysis Results:[/bold]")
        console.print(f"Error: [red]{error_context.error_message}[/red]")
        console.print(f"File: [blue]{error_context.file_path}:{error_context.line_number}[/blue]")
        
        if not suggestions:
            console.print("[yellow]No suggestions found.[/yellow]")
            return
        
        # Create table for suggestions
        table = Table(title="Fix Suggestions")
        table.add_column("Rank", style="cyan", no_wrap=True)
        table.add_column("Title", style="bold")
        table.add_column("Description", style="dim")
        table.add_column("Agent", style="green")
        table.add_column("Confidence", style="yellow")
        
        for i, suggestion in enumerate(suggestions, 1):
            table.add_row(
                str(i),
                suggestion.title,
                suggestion.description[:50] + "..." if len(suggestion.description) > 50 else suggestion.description,
                suggestion.agent_source,
                f"{suggestion.confidence_score:.2f}"
            )
        
        console.print(table)
        
        # Show detailed suggestions
        for i, suggestion in enumerate(suggestions, 1):
            console.print(f"\n[bold cyan]Suggestion {i}:[/bold cyan]")
            console.print(f"[bold]{suggestion.title}[/bold]")
            console.print(f"[dim]{suggestion.description}[/dim]")
            
            if suggestion.code_snippet:
                console.print(Panel(
                    suggestion.code_snippet,
                    title="Code Snippet",
                    border_style="blue"
                ))
            
            if suggestion.explanation:
                console.print(f"[italic]Explanation:[/italic] {suggestion.explanation}")
            
            console.print(f"Agent: [green]{suggestion.agent_source}[/green] | Confidence: [yellow]{suggestion.confidence_score:.2f}[/yellow]")
    
    def get_status(self) -> dict:
        """Get system status."""
        return {
            "running": self.running,
            "orchestrator": "running" if self.running else "stopped",
            "log_agent": "running" if self.running else "stopped",
            "code_agent": "running" if self.running else "stopped",
            "active_sessions": len(self.orchestrator.active_sessions),
            "suggestion_history": len(self.orchestrator.suggestion_history),
        }


# Global system instance
bugfree_system = BugfreeSystem()


@app.command()
def start():
    """Start the Bugfree Multi-Agent System."""
    async def _start():
        await bugfree_system.start()
    
    asyncio.run(_start())


@app.command()
def stop():
    """Stop the Bugfree Multi-Agent System."""
    async def _stop():
        await bugfree_system.stop()
    
    asyncio.run(_stop())


@app.command()
def status():
    """Show system status."""
    status_info = bugfree_system.get_status()
    
    table = Table(title="Bugfree System Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    
    table.add_row("System", "🟢 Running" if status_info["running"] else "🔴 Stopped")
    table.add_row("Orchestrator", status_info["orchestrator"].title())
    table.add_row("Log Agent", status_info["log_agent"].title())
    table.add_row("Code Agent", status_info["code_agent"].title())
    table.add_row("Active Sessions", str(status_info["active_sessions"]))
    table.add_row("Suggestion History", str(status_info["suggestion_history"]))
    
    console.print(table)


@app.command()
def analyze(
    error: str = typer.Argument(..., help="Error message"),
    file: str = typer.Argument(..., help="File path where error occurred"),
    line: int = typer.Argument(..., help="Line number where error occurred")
):
    """Analyze a specific error."""
    async def _analyze():
        await bugfree_system.process_error(error, file, line)
    
    asyncio.run(_analyze())


@app.command()
def demo():
    """Run a demo with sample errors."""
    async def _demo():
        console.print("[bold blue]Running Bugfree Demo[/bold blue]")
        
        # Start the system
        await bugfree_system.start()
        
        # Demo errors
        demo_errors = [
            {
                "message": "NameError: name 'undefined_variable' is not defined",
                "file": "example.py",
                "line": 10
            },
            {
                "message": "TypeError: 'int' object is not callable",
                "file": "calculator.py",
                "line": 25
            },
            {
                "message": "ModuleNotFoundError: No module named 'requests'",
                "file": "api_client.py",
                "line": 5
            }
        ]
        
        for error in demo_errors:
            console.print(f"\n[bold]Demo Error:[/bold] {error['message']}")
            await bugfree_system.process_error(
                error["message"], 
                error["file"], 
                error["line"]
            )
            await asyncio.sleep(2)  # Pause between errors
        
        await bugfree_system.stop()
    
    asyncio.run(_demo())


@app.command()
def test_network():
    """Test the network connectivity between agents."""
    async def _test_network():
        console.print("[bold blue]Testing Network Connectivity...[/bold blue]")
        
        try:
            # Start the system
            await bugfree_system.start()
            
            # Test basic error processing
            test_error = ErrorContext(
                error_type=ErrorType.NAME_ERROR,
                error_message="NameError: name 'test_var' is not defined",
                file_path="test.py",
                line_number=1,
                severity=ErrorSeverity.MEDIUM,
            )
            
            suggestions = await bugfree_system.orchestrator.process_error(test_error)
            
            if suggestions:
                console.print("[bold green]✓ Network test successful![/bold green]")
                console.print(f"Received {len(suggestions)} suggestions from agents")
            else:
                console.print("[bold yellow]⚠ Network test completed but no suggestions received[/bold yellow]")
            
            await bugfree_system.stop()
            
        except Exception as e:
            console.print(f"[bold red]✗ Network test failed: {e}[/bold red]")
            await bugfree_system.stop()
    
    asyncio.run(_test_network())


if __name__ == "__main__":
    app()
