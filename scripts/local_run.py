#!/usr/bin/env python3
"""
Local development runner for Publer MCP server.

This script helps with local development and testing of the MCP server.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


def run_server(transport: str = "stdio", port: int = 8000):
    """
    Run the Publer MCP server locally.
    
    Args:
        transport: Transport method ('stdio' or 'sse')
        port: Port for SSE transport (ignored for stdio)
    """
    try:
        from publer_mcp.server import app
        
        print(f"🚀 Starting Publer MCP Server...")
        print(f"📡 Transport: {transport}")
        
        if transport == "stdio":
            print("🔌 Running in stdio mode for local MCP client testing")
            print("ℹ️  Connect your MCP client to this process")
            # TODO: Implement stdio transport runner
            print("📝 TODO: Implement stdio transport - server structure ready!")
            
        elif transport == "sse":
            print(f"🌐 Running in SSE mode on port {port}")
            print(f"🔗 Access at: http://localhost:{port}")
            # TODO: Implement SSE transport runner
            print("📝 TODO: Implement SSE transport - server structure ready!")
            
        else:
            print(f"❌ Unknown transport: {transport}")
            sys.exit(1)
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure to install dependencies: pip install -e .")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)


def main():
    """
    Main entry point for local development runner.
    """
    parser = argparse.ArgumentParser(
        description="Run Publer MCP server locally for development"
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport method (default: stdio)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for SSE transport (default: 8000)"
    )
    
    args = parser.parse_args()
    
    # Check if we're in a development environment
    if not (Path.cwd() / "pyproject.toml").exists():
        print("⚠️  Warning: Not running from project root")
        print("💡 Consider running from the project root directory")
    
    run_server(transport=args.transport, port=args.port)


if __name__ == "__main__":
    main()