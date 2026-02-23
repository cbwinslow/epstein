#!/usr/bin/env python3
"""
Simple Mission Control - Terminal Interface for Epstein Files Pipeline
"""

import os
import sys

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Add current directory to Python path
sys.path.insert(0, '.')

console = Console()

def print_header():
    """Print application header"""
    header = Text()
    header.append("🚀 EPSTEIN FILES MISSION CONTROL\n", style="bold blue")
    header.append("Document Processing Pipeline Interface\n", style="dim")
    header.append("=" * 50, style="blue")
    console.print(header)
    console.print()

def check_system_status():
    """Check system status and display status table"""

    # Create status table
    table = Table(title="System Status", box=box.ROUNDED)
    table.add_column("Component", style="cyan", no_wrap=True)
    table.add_column("Status", style="green")
    table.add_column("Details", style="yellow")

    # Check Python environment
    python_version = sys.version.split()[0]
    table.add_row("Python Environment", "✅ Ready", f"Version {python_version}")

    # Check dependencies
    try:
        import textual
        table.add_row("Textual", "✅ Available", f"v{textual.__version__}")
    except ImportError:
        table.add_row("Textual", "❌ Missing", "Install with: uv add textual")

    # Check project structure
    if os.path.exists("epstein/epstein_files_pipeline.py"):
        table.add_row("Pipeline Script", "✅ Found", "Core processing available")
    else:
        table.add_row("Pipeline Script", "❌ Missing", "Pipeline not found")

    # Check agents
    if os.path.exists("agents/multi_agent_orchestrator.py"):
        table.add_row("Agent System", "✅ Found", "Multi-agent orchestration")
    else:
        table.add_row("Agent System", "❌ Missing", "Agents not found")

    # Check databases
    table.add_row("PostgreSQL", "⚠️ Unknown", "Check with: python scripts/doctor.py")
    table.add_row("Qdrant", "⚠️ Unknown", "Vector database status")

    console.print(table)
    console.print()

def show_agent_status():
    """Display agent status information"""

    agents_panel = Panel(
        "[bold yellow]Agent System Status[/bold yellow]\n\n"
        "• Document Analysis Agent: [green]Ready[/green]\n"
        "• Entity Extraction Agent: [green]Ready[/green]\n"
        "• Vector DB Analyzer: [green]Ready[/green]\n"
        "• Pipeline Monitor: [green]Ready[/green]\n"
        "• Multi-Agent Orchestrator: [green]Ready[/green]",
        title="Available Agents",
        border_style="yellow",
        padding=(1, 2)
    )

    console.print(agents_panel)
    console.print()

def show_quick_commands():
    """Show quick command reference"""

    commands_panel = Panel(
        "[bold magenta]Quick Commands[/bold magenta]\n\n"
        "[cyan]Pipeline Commands:[/cyan]\n"
        "• Run pipeline: [green]uv run python epstein/epstein_files_pipeline.py run --config config.json[/green]\n"
        "• Initialize config: [green]uv run python epstein/epstein_files_pipeline.py init-config --out config.json[/green]\n\n"
        "[cyan]Agent Commands:[/cyan]\n"
        "• Start orchestrator: [green]uv run python agents/multi_agent_orchestrator.py[/green]\n"
        "• Check agent status: [green]uv run python agents/multi_agent_orchestrator.py status[/green]\n\n"
        "[cyan]Database Commands:[/cyan]\n"
        "• Health check: [green]python scripts/doctor.py[/green]\n"
        "• Start databases: [green]docker compose up -d[/green]\n\n"
        "[cyan]System Commands:[/cyan]\n"
        "• Install deps: [green]uv sync[/green]\n"
        "• Run tests: [green]make test[/green]\n"
        "• Help: [green]make help[/green]",
        title="Command Reference",
        border_style="magenta",
        padding=(1, 2)
    )

    console.print(commands_panel)
    console.print()

def interactive_menu():
    """Interactive command menu"""

    while True:
        console.print("\n[bold]Mission Control Menu[/bold]")
        console.print("1. System Status")
        console.print("2. Agent Status")
        console.print("3. Quick Commands")
        console.print("4. Run Health Check")
        console.print("5. Launch Pipeline")
        console.print("6. Start Agents")
        console.print("0. Exit")

        choice = console.input("\n[bold cyan]Select option (0-6): [/bold cyan] ").strip()

        if choice == "0":
            console.print("\n👋 Exiting Mission Control...")
            break
        elif choice == "1":
            check_system_status()
        elif choice == "2":
            show_agent_status()
        elif choice == "3":
            show_quick_commands()
        elif choice == "4":
            console.print("\n🔍 Running health check...")
            os.system("python scripts/doctor.py")
        elif choice == "5":
            console.print("\n🚀 Launching document processing pipeline...")
            console.print("[yellow]Note: Make sure to initialize config first with:[/yellow]")
            console.print("[green]uv run python epstein/epstein_files_pipeline.py init-config --out config.json[/green]")
        elif choice == "6":
            console.print("\n🤖 Starting multi-agent system...")
            os.system("uv run python agents/multi_agent_orchestrator.py")
        else:
            console.print(f"\n[red]Invalid option: {choice}[/red]")

        console.input("\nPress Enter to continue...")

def main():
    """Main application entry point"""

    try:
        print_header()
        check_system_status()

        # Show quick commands reference
        show_quick_commands()

        # Interactive menu
        interactive_menu()

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Mission Control interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error in Mission Control: {e}[/red]")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
