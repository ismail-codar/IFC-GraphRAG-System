#!/usr/bin/env python
"""
BIMConverse CLI Module

Command-line interface for interacting with IFC knowledge graphs using natural language queries.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import textwrap
import datetime

# Platform-specific readline handling
try:
    import readline
except ImportError:
    try:
        import pyreadline3 as readline
    except ImportError:
        # If neither is available, we'll continue without readline support
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich import box
from rich.columns import Columns
from rich.text import Text

from core import BIMConverseRAG, create_config_file

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BIMConverseCLI")

# Create Rich console for pretty printing
console = Console()

def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="BIMConverse - Natural language querying for IFC knowledge graphs",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--config", "-c",
        type=str,
        help="Path to configuration file"
    )
    
    parser.add_argument(
        "--create-config",
        action="store_true",
        help="Create a new configuration file"
    )
    
    parser.add_argument(
        "--query", "-q",
        type=str,
        help="Execute a single query and exit"
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Display database statistics and exit"
    )
    
    parser.add_argument(
        "--no-sources",
        action="store_true",
        help="Don't include source information in query results"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format for query results"
    )
    
    parser.add_argument(
        "--save",
        type=str,
        help="Save query results to file"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--context",
        action="store_true",
        help="Enable conversation context"
    )
    
    return parser

def create_configuration_wizard() -> Dict[str, Any]:
    """Interactive wizard for creating a configuration file."""
    console.print(Panel.fit(
        "BIMConverse Configuration Wizard",
        subtitle="Create a new configuration for your building model",
        padding=(1, 2),
        title_align="center"
    ))
    
    console.print("\n[bold]Project Information[/bold]")
    project_name = console.input("[cyan]Project name:[/cyan] ")
    
    console.print("\n[bold]Neo4j Connection[/bold]")
    console.print("Enter your Neo4j database connection details:")
    neo4j_uri = console.input("[cyan]Neo4j URI[/cyan] [dim](default: neo4j://localhost:7687)[/dim]: ") or "neo4j://localhost:7687"
    neo4j_username = console.input("[cyan]Username[/cyan] [dim](default: neo4j)[/dim]: ") or "neo4j"
    neo4j_password = console.input("[cyan]Password[/cyan] [dim](default: test1234)[/dim]: ", password=True) or "test1234"
    
    console.print("\n[bold]OpenAI API[/bold]")
    console.print("Enter your OpenAI API key for embeddings and LLM:")
    openai_api_key = console.input("[cyan]OpenAI API Key[/cyan]: ", password=True) or ""
    
    console.print("\n[bold]Conversation Context[/bold]")
    context_enabled = console.input("[cyan]Enable conversation context?[/cyan] [dim](y/n, default: n)[/dim]: ").lower() == 'y'
    max_history = console.input("[cyan]Maximum conversation history length[/cyan] [dim](default: 10)[/dim]: ") or "10"
    
    console.print("\n[bold]Output Configuration[/bold]")
    output_path = console.input("[cyan]Save configuration to[/cyan] [dim](default: config.json)[/dim]: ") or "config.json"
    
    # Create and return the configuration
    return {
        "output_path": output_path,
        "neo4j_uri": neo4j_uri,
        "neo4j_username": neo4j_username,
        "neo4j_password": neo4j_password,
        "openai_api_key": openai_api_key,
        "project_name": project_name,
        "context_enabled": context_enabled,
        "max_history": int(max_history)
    }

def display_statistics(stats: Dict[str, Any]):
    """Display database statistics in a formatted table."""
    console.print(Panel(
        "[bold]Knowledge Graph Statistics[/bold]",
        subtitle=f"Total: {stats['nodes']} nodes, {stats['relationships']} relationships",
        padding=(1, 2)
    ))
    
    # Node labels table
    label_table = Table(title="Node Types", box=box.ROUNDED)
    label_table.add_column("Label", style="cyan")
    label_table.add_column("Count", justify="right", style="green")
    
    for label, count in stats.get('labels', {}).items():
        # Clean up the label format (remove brackets and quotes)
        clean_label = label.replace("[", "").replace("]", "").replace("'", "")
        label_table.add_row(clean_label, str(count))
    
    console.print(label_table)
    
    # Relationship types table
    rel_table = Table(title="Relationship Types", box=box.ROUNDED)
    rel_table.add_column("Type", style="cyan")
    rel_table.add_column("Count", justify="right", style="green")
    
    for rel_type, count in stats.get('relationship_types', {}).items():
        rel_table.add_row(rel_type, str(count))
    
    console.print(rel_table)

def display_conversation_settings(settings: Dict[str, Any]):
    """Display conversation context settings."""
    enabled = settings["enabled"]
    status = "[green]Enabled[/green]" if enabled else "[yellow]Disabled[/yellow]"
    
    console.print(Panel(
        f"Conversation Context: {status}\n"
        f"Max History Length: {settings['max_history_length']}\n"
        f"Current History: {settings['current_history_length']} exchanges",
        title="Conversation Context Settings",
        border_style="cyan",
        padding=(1, 2)
    ))

def display_conversation_history(history):
    """Display conversation history."""
    if not history:
        console.print("[yellow]No conversation history.[/yellow]")
        return
    
    console.print(Panel(
        "Conversation History",
        subtitle=f"({len(history)} exchanges)",
        border_style="cyan",
        padding=(1, 0)
    ))
    
    for i, (question, answer) in enumerate(history):
        q_text = Text(f"Q: {question}", style="cyan")
        a_text = Text(f"A: {answer}", style="green")
        
        console.print(f"\n[bold]Exchange {i+1}:[/bold]")
        console.print(q_text)
        console.print(a_text)
        
        if i < len(history) - 1:
            console.print("---")

def format_query_result(
    result: Dict[str, Any],
    output_format: str = "text",
    include_sources: bool = True
) -> str:
    """Format the query result according to the specified output format."""
    context_info = " (with conversation context)" if result.get("context_used", False) else ""
    
    if output_format == "json":
        return json.dumps(result, indent=2)
    
    elif output_format == "markdown":
        md_output = f"# Query{context_info}: {result['question']}\n\n"
        md_output += f"## Answer\n\n{result['answer']}\n\n"
        
        if include_sources and "cypher" in result:
            md_output += f"## Generated Cypher Query\n\n```cypher\n{result['cypher']}\n```\n\n"
            
        if include_sources and "sources" in result:
            md_output += "## Sources\n\n"
            for i, source in enumerate(result.get("sources", [])):
                md_output += f"### Source {i+1}\n\n"
                md_output += f"```\n{source}\n```\n\n"
                
        return md_output
    
    else:  # Text format
        text_output = f"Q{context_info}: {result['question']}\n\n"
        text_output += f"A: {result['answer']}\n"
        
        if include_sources and "cypher" in result:
            text_output += f"\nGenerated Cypher Query:\n{result['cypher']}\n"
            
        if include_sources and "sources" in result:
            text_output += "\nSources:\n"
            for i, source in enumerate(result.get("sources", [])):
                text_output += f"\n--- Source {i+1} ---\n{source}\n"
                
        return text_output

def save_result_to_file(content: str, filename: Optional[str] = None, format: str = "text") -> str:
    """Save query result to a file."""
    if not filename:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = {"text": "txt", "json": "json", "markdown": "md"}[format]
        filename = f"bimconverse_query_{timestamp}.{ext}"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    
    return filename

def print_welcome_message():
    """Print welcome message with usage instructions."""
    welcome_text = """
    BIMConverse - Query your building model using natural language

    Type your questions about the building model to get answers.
    Special commands:
      :help       - Display this help message
      :stats      - Display database statistics
      :exit       - Exit the program
      :save FILE  - Save last query result to FILE
      :clear      - Clear the screen
      
    Context management:
      :context on       - Enable conversation context
      :context off      - Disable conversation context
      :context status   - Show context settings
      :context history  - Show conversation history
      :context clear    - Clear conversation history
      :context length N - Set maximum history length to N
    """
    
    console.print(Panel(
        welcome_text,
        title="Welcome to BIMConverse",
        subtitle="Press Ctrl+C to exit",
        padding=(1, 2),
        border_style="cyan"
    ))

def handle_context_command(bimconverse: BIMConverseRAG, command_parts: List[str]):
    """Handle context-related commands."""
    if len(command_parts) == 1:
        # Show context status by default
        settings = bimconverse.get_conversation_settings()
        display_conversation_settings(settings)
        return
    
    subcommand = command_parts[1].lower()
    
    if subcommand in ("on", "enable"):
        bimconverse.set_context_enabled(True)
        console.print("[green]Conversation context enabled.[/green]")
    
    elif subcommand in ("off", "disable"):
        bimconverse.set_context_enabled(False)
        console.print("[yellow]Conversation context disabled.[/yellow]")
    
    elif subcommand == "status":
        settings = bimconverse.get_conversation_settings()
        display_conversation_settings(settings)
    
    elif subcommand == "history":
        history = bimconverse.get_conversation_history()
        display_conversation_history(history)
    
    elif subcommand == "clear":
        bimconverse.clear_conversation_history()
        console.print("[green]Conversation history cleared.[/green]")
    
    elif subcommand == "length" and len(command_parts) > 2:
        try:
            length = int(command_parts[2])
            bimconverse.set_max_history_length(length)
            console.print(f"[green]Maximum history length set to {length}.[/green]")
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
    
    else:
        console.print("[yellow]Unknown context command. Try :help for available commands.[/yellow]")

def interactive_loop(bimconverse: BIMConverseRAG, include_sources: bool = True, output_format: str = "text"):
    """Run an interactive query loop."""
    print_welcome_message()
    
    history = []
    last_result = None
    
    while True:
        try:
            # Get user input
            user_query = console.input("\n[bold cyan]> [/bold cyan]")
            
            # Check for special commands
            if user_query.lower() in (':q', ':quit', ':exit'):
                break
                
            elif user_query.lower() in (':help', ':h'):
                print_welcome_message()
                continue
                
            elif user_query.lower() in (':stats', ':stat', ':s'):
                stats = bimconverse.get_stats()
                display_statistics(stats)
                continue
                
            elif user_query.lower() in (':clear', ':cls', ':c'):
                console.clear()
                continue
                
            elif user_query.lower().startswith(':context'):
                parts = user_query.split()
                handle_context_command(bimconverse, parts)
                continue
                
            elif user_query.lower().startswith(':save'):
                if not last_result:
                    console.print("[yellow]No query result to save.[/yellow]")
                    continue
                    
                parts = user_query.split(maxsplit=1)
                filename = parts[1] if len(parts) > 1 else None
                
                saved_path = save_result_to_file(
                    format_query_result(last_result, output_format, include_sources),
                    filename,
                    output_format
                )
                console.print(f"[green]Result saved to:[/green] {saved_path}")
                continue
                
            elif not user_query.strip():
                continue
            
            # Process the query
            with console.status("[bold green]Processing query...[/bold green]"):
                result = bimconverse.query(user_query, include_sources=include_sources)
                last_result = result
                history.append((user_query, result))
            
            # Format and display the result
            if output_format == "markdown":
                console.print(Markdown(format_query_result(result, output_format, include_sources)))
            else:
                console.print(format_query_result(result, output_format, include_sources))
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Exiting...[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")

def main():
    """Main entry point for BIMConverse CLI."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Set logging level based on verbose flag
    if args.verbose:
        logging.getLogger("BIMConverse").setLevel(logging.DEBUG)
        logging.getLogger("BIMConverseCLI").setLevel(logging.DEBUG)
    
    # Create configuration file if requested
    if args.create_config:
        config_data = create_configuration_wizard()
        
        # Create a new configuration file with conversation settings
        config = {
            "project_name": config_data["project_name"],
            "neo4j": {
                "uri": config_data["neo4j_uri"],
                "username": config_data["neo4j_username"],
                "password": config_data["neo4j_password"]
            },
            "openai": {
                "api_key": config_data["openai_api_key"]
            },
            "conversation": {
                "enabled": config_data["context_enabled"],
                "max_history_length": config_data["max_history"]
            }
        }
        
        # Create the configuration file
        try:
            output_path = config_data["output_path"]
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(config, f, indent=2)
            console.print(f"[green]Configuration created at:[/green] {output_path}")
            
            if not args.config:
                args.config = output_path
                
        except Exception as e:
            console.print(f"[red]Error creating configuration file:[/red] {e}")
            sys.exit(1)
    
    # Initialize BIMConverseRAG
    try:
        bimconverse = BIMConverseRAG(config_path=args.config)
        
        # Apply command-line context setting if provided
        if args.context:
            bimconverse.set_context_enabled(True)
            logger.info("Conversation context enabled from command line")
            
    except Exception as e:
        console.print(f"[red]Error initializing BIMConverse:[/red] {e}")
        sys.exit(1)
    
    # Display statistics if requested
    if args.stats:
        stats = bimconverse.get_stats()
        display_statistics(stats)
        bimconverse.close()
        sys.exit(0)
    
    # Execute a single query if provided
    if args.query:
        with console.status("[bold green]Processing query...[/bold green]"):
            result = bimconverse.query(
                args.query, 
                include_sources=not args.no_sources,
                use_context=args.context
            )
        
        formatted_result = format_query_result(
            result, 
            output_format=args.output,
            include_sources=not args.no_sources
        )
        
        if args.save:
            saved_path = save_result_to_file(formatted_result, args.save, args.output)
            console.print(f"[green]Result saved to:[/green] {saved_path}")
        
        if args.output == "markdown":
            console.print(Markdown(formatted_result))
        else:
            console.print(formatted_result)
            
        bimconverse.close()
        sys.exit(0)
    
    # Start interactive loop
    try:
        interactive_loop(
            bimconverse,
            include_sources=not args.no_sources,
            output_format=args.output
        )
    finally:
        bimconverse.close()

if __name__ == "__main__":
    main() 