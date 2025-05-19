#!/usr/bin/env python
"""
BIMConverse - Natural language querying for IFC knowledge graphs

This is the main entry point for BIMConverse, which can be used to launch
the CLI or web interface.
"""

import sys
import logging
import argparse
from typing import List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BIMConverse")

def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="BIMConverse - Natural language querying for IFC knowledge graphs",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # CLI command
    cli_parser = subparsers.add_parser("cli", help="Run BIMConverse CLI")
    # Add CLI arguments - will be forwarded to cli.py
    
    # Web UI command
    web_parser = subparsers.add_parser("web", help="Run BIMConverse web interface")
    web_parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to run the web interface on"
    )
    web_parser.add_argument(
        "--port",
        type=int,
        default=7860,
        help="Port to run the web interface on"
    )
    web_parser.add_argument(
        "--config", "-c",
        type=str,
        help="Path to configuration file"
    )
    web_parser.add_argument(
        "--share",
        action="store_true",
        help="Create a public URL"
    )
    
    return parser

def main(args: Optional[List[str]] = None):
    """Main entry point for BIMConverse."""
    parser = create_parser()
    parsed_args = parser.parse_args(args)
    
    if not parsed_args.command:
        parser.print_help()
        sys.exit(1)
    
    if parsed_args.command == "cli":
        # Import CLI module here to avoid circular imports
        from cli import main as cli_main
        # Forward all remaining arguments to the CLI
        cli_main()
    
    elif parsed_args.command == "web":
        logger.info("Web interface not implemented yet")
        logger.info("Use 'bimconverse cli' to run the CLI")
        # This will be implemented in Phase 4 Part 2
        # from webui import main as web_main
        # web_main(
        #    host=parsed_args.host,
        #    port=parsed_args.port,
        #    config_path=parsed_args.config,
        #    share=parsed_args.share
        # )
    
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main() 