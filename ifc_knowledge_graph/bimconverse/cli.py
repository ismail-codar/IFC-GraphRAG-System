#!/usr/bin/env python
"""
BIMConverse CLI

This module implements the command-line interface for BIMConverse,
allowing natural language querying of IFC knowledge graphs.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

try:
    import readline  # For command history on Unix
except ImportError:
    try:
        import pyreadline3 as readline  # For Windows
    except ImportError:
        pass  # Readline is not available

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.columns import Columns
from rich.text import Text
from rich.prompt import Prompt, Confirm

from core import BIMConverseRAG, create_config_file

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BIMConverse")

# Create a Rich console for pretty output
console = Console()

# Special commands in interactive mode
SPECIAL_COMMANDS = {
    "/help": "Show this help message",
    "/quit": "Exit the application",
    "/exit": "Exit the application",
    "/context on": "Enable conversation context",
    "/context off": "Disable conversation context",
    "/context clear": "Clear conversation context",
    "/context status": "Show conversation context status",
    "/stats": "Show database statistics",
}

def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="BIMConverse - Natural language querying for IFC knowledge graphs",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--config", "-c",
        type=str,
        default="config.json",
        help="Path to configuration file"
    )
    
    parser.add_argument(
        "--create-config",
        action="store_true",
        help="Create a new configuration file"
    )
    
    parser.add_argument(
        "--uri",
        type=str,
        help="Neo4j connection URI (overrides config)"
    )
    
    parser.add_argument(
        "--username",
        type=str,
        help="Neo4j username (overrides config)"
    )
    
    parser.add_argument(
        "--password",
        type=str,
        help="Neo4j password (overrides config)"
    )
    
    parser.add_argument(
        "--api-key",
        type=str,
        help="OpenAI API key (overrides config)"
    )
    
    parser.add_argument(
        "--query", "-q",
        type=str,
        help="Run a single query without entering interactive mode"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        choices=["text", "json", "markdown"],
        default="markdown",
        help="Output format"
    )
    
    parser.add_argument(
        "--context",
        action="store_true",
        help="Enable conversation context"
    )
    
    return parser

def print_header():
    """Print the BIMConverse header."""
    console.print(Panel.fit(
        "[bold blue]BIMConverse[/bold blue] - [italic]Natural language querying for IFC knowledge graphs[/italic]",
        border_style="blue"
    ))
    console.print()

def handle_special_command(command: str, bimconverse: BIMConverseRAG) -> bool:
    """
    Handle a special command.
    
    Args:
        command: The command to handle
        bimconverse: The BIMConverseRAG instance
        
    Returns:
        True if the user wants to exit, False otherwise
    """
    if command in ["/quit", "/exit"]:
        console.print("[italic]Exiting BIMConverse...[/italic]")
        return True
    
    elif command == "/help":
        console.print(Panel("[bold]Available commands:[/bold]", border_style="blue"))
        for cmd, desc in SPECIAL_COMMANDS.items():
            console.print(f"  [bold blue]{cmd}[/bold blue]: {desc}")
        console.print()
    
    elif command == "/context on":
        bimconverse.set_context_enabled(True)
        console.print("[green]Conversation context enabled[/green]")
    
    elif command == "/context off":
        bimconverse.set_context_enabled(False)
        console.print("[yellow]Conversation context disabled[/yellow]")
    
    elif command == "/context clear":
        bimconverse.clear_conversation_history()
        console.print("[yellow]Conversation context cleared[/yellow]")
    
    elif command == "/context status":
        settings = bimconverse.get_conversation_settings()
        console.print(Panel(
            f"[bold]Conversation Context:[/bold]\n"
            f"Enabled: {'[green]Yes[/green]' if settings['enabled'] else '[red]No[/red]'}\n"
            f"Max History Length: {settings['max_history_length']}\n"
            f"Current History Length: {settings['current_history_length']}",
            border_style="blue"
        ))
    
    elif command == "/stats":
        stats = bimconverse.get_stats()
        
        if "error" in stats:
            console.print(f"[red]Error getting statistics: {stats['error']}[/red]")
            return False
        
        console.print(Panel(
            f"[bold]Database Statistics:[/bold]\n"
            f"Nodes: {stats['nodes']}\n"
            f"Relationships: {stats['relationships']}",
            border_style="blue"
        ))
        
        if 'labels' in stats and stats['labels']:
            console.print("\n[bold]Node Labels:[/bold]")
            for label, count in stats['labels'].items():
                console.print(f"  {label}: {count}")
        
        if 'relationship_types' in stats and stats['relationship_types']:
            console.print("\n[bold]Relationship Types:[/bold]")
            for rel_type, count in stats['relationship_types'].items():
                console.print(f"  {rel_type}: {count}")
    
    else:
        console.print(f"[red]Unknown command: {command}[/red]")
        console.print("[italic]Type /help to see available commands[/italic]")
    
    return False

def format_result(result: Dict[str, Any], output_format: str) -> None:
    """
    Format and print the query result.
    
    Args:
        result: The query result
        output_format: The output format (text, json, markdown)
    """
    if output_format == "json":
        # Output as JSON
        console.print(json.dumps(result, indent=2))
        return
    
    if "error" in result and result["error"]:
        console.print(f"[red]Error: {result['answer']}[/red]")
        return
    
    if output_format == "text":
        # Simple text output
        console.print(result["answer"])
        if result.get("cypher_query"):
            console.print("\nGenerated Cypher:")
            console.print(result["cypher_query"])
        return
    
    # Default: Markdown format with rich formatting
    answer_md = Markdown(result["answer"])
    
    panels = []
    
    # Main answer panel
    panels.append(Panel(
        answer_md,
        title="[bold blue]Answer[/bold blue]",
        border_style="blue"
    ))
    
    # If we have a Cypher query, add it as a panel
    if result.get("cypher_query"):
        panels.append(Panel(
            result["cypher_query"],
            title="[bold blue]Generated Cypher[/bold blue]",
            border_style="dim"
        ))
    
    # Print the panels
    if len(panels) == 1:
        console.print(panels[0])
    else:
        console.print(Columns(panels))
    
    # Print sources if available
    if result.get("sources") and len(result["sources"]) > 0:
        console.print("\n[bold]Sources:[/bold]")
        for i, source in enumerate(result["sources"]):
            source_content = source.get("content", "")
            if source_content:
                console.print(f"  {i+1}. {source_content[:100]}...")

def interactive_mode(bimconverse: BIMConverseRAG, output_format: str):
    """
    Run the interactive mode.
    
    Args:
        bimconverse: The BIMConverseRAG instance
        output_format: The output format
    """
    print_header()
    console.print("[italic]Type /help to see available commands[/italic]")
    console.print("[italic]Type /quit to exit[/italic]")
    console.print()
    
    while True:
        try:
            # Get input from user
            query = Prompt.ask("[bold blue]BIMConverse[/bold blue]")
            
            # Check if this is a special command
            if query.startswith("/"):
                if handle_special_command(query, bimconverse):
                    break
                continue
            
            if not query.strip():
                continue
            
            # Execute the query
            result = bimconverse.query(query)
            
            # Format and print the result
            format_result(result, output_format)
            console.print()
            
        except KeyboardInterrupt:
            console.print("\n[italic]Interrupted by user. Type /quit to exit.[/italic]")
        except Exception as e:
            logger.error(f"Error in interactive mode: {str(e)}")
            console.print(f"[red]Error: {str(e)}[/red]")

def create_config_wizard():
    """Run the configuration wizard to create a config file."""
    print_header()
    console.print("[bold]Configuration Wizard[/bold]")
    console.print("This wizard will help you create a configuration file for BIMConverse.")
    console.print()
    
    # Get configuration values
    config_path = Prompt.ask("Config file path", default="config.json")
    
    neo4j_uri = Prompt.ask("Neo4j URI", default="neo4j://localhost:7687")
    neo4j_username = Prompt.ask("Neo4j username", default="neo4j")
    neo4j_password = Prompt.ask("Neo4j password", default="test1234", password=True)
    
    openai_api_key = os.environ.get("OPENAI_API_KEY", "")
    if not openai_api_key:
        openai_api_key = Prompt.ask("OpenAI API key", password=True)
    
    project_name = Prompt.ask("Project name", default="IFC Building Project")
    context_enabled = Confirm.ask("Enable conversation context", default=False)
    max_history_length = int(Prompt.ask("Max conversation history length", default="10"))
    
    # Create the config file
    try:
        config_file = create_config_file(
            output_path=config_path,
            neo4j_uri=neo4j_uri,
            neo4j_username=neo4j_username,
            neo4j_password=neo4j_password,
            openai_api_key=openai_api_key,
            project_name=project_name,
            context_enabled=context_enabled,
            max_history_length=max_history_length
        )
        
        console.print(f"[green]Configuration file created: {config_file}[/green]")
        
    except Exception as e:
        logger.error(f"Error creating configuration file: {str(e)}")
        console.print(f"[red]Error creating configuration file: {str(e)}[/red]")
        sys.exit(1)

def main(args: Optional[List[str]] = None):
    """
    Main entry point for the CLI.
    
    Args:
        args: Command line arguments (for testing)
    """
    parser = create_parser()
    parsed_args = parser.parse_args(args)
    
    # Create a new configuration file if requested
    if parsed_args.create_config:
        create_config_wizard()
        return
    
    # Parse config file path
    config_path = parsed_args.config
    if config_path and not os.path.isfile(config_path):
        logger.warning(f"Configuration file not found: {config_path}")
        if not parsed_args.uri or not parsed_args.username or not parsed_args.password:
            logger.error("Neo4j connection details must be provided either in a config file or as arguments")
            parser.print_help()
            sys.exit(1)
        config_path = None
    
    try:
        # Initialize BIMConverseRAG
        bimconverse = BIMConverseRAG(
            config_path=config_path,
            neo4j_uri=parsed_args.uri,
            neo4j_username=parsed_args.username,
            neo4j_password=parsed_args.password,
            openai_api_key=parsed_args.api_key
        )
        
        # Set conversation context if enabled
        if parsed_args.context:
            bimconverse.set_context_enabled(True)
        
        # Run a single query if provided
        if parsed_args.query:
            result = bimconverse.query(parsed_args.query)
            format_result(result, parsed_args.output)
        else:
            # Run interactive mode
            interactive_mode(bimconverse, parsed_args.output)
        
        # Close connection
        bimconverse.close()
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main() 