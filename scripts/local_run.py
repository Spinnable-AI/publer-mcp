#!/usr/bin/env python3
"""
Local development runner for Publer MCP Server

This script helps run the MCP server locally for testing and development.
Supports both stdio and SSE transport modes.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from publer_mcp.server import app, health_check
import mcp.server.stdio
from mcp.server.models import InitializationOptions

def check_environment():
    """Check if required environment variables are set"""
    api_key = os.getenv("PUBLER_API_KEY")
    workspace_id = os.getenv("PUBLER_WORKSPACE_ID")
    
    if not api_key:
        print("⚠️  PUBLER_API_KEY environment variable not set")
        print("   Set it with: export PUBLER_API_KEY=your_api_key")
    
    if not workspace_id:
        print("⚠️  PUBLER_WORKSPACE_ID environment variable not set") 
        print("   Set it with: export PUBLER_WORKSPACE_ID=your_workspace_id")
    
    if api_key and workspace_id:
        print("✅ Environment variables configured")
        return True
    else:
        print("\n💡 You can still test the server, but tools will show configuration errors")
        return False

async def run_stdio():
    """Run MCP server with stdio transport (for Claude Desktop)"""
    print("🚀 Starting Publer MCP Server (stdio transport)")
    print("   Use this mode for Claude Desktop integration")
    print("   Press Ctrl+C to stop")
    print()
    
    try:
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="publer-mcp",
                    server_version="0.1.0",
                    capabilities={}
                )
            )
    except KeyboardInterrupt:
        print("\n👋 Publer MCP Server stopped")

async def run_health_check():
    """Test server health check"""
    print("🔍 Testing server health check...")
    try:
        result = await health_check()
        print(f"✅ Health check passed: {result}")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

async def main():
    """Main entry point"""
    print("🎯 Publer MCP Server - Local Development")
    print("=" * 50)
    
    # Check environment
    env_ok = check_environment()
    print()
    
    # Run health check
    health_ok = await run_health_check()
    print()
    
    if len(sys.argv) > 1 and sys.argv[1] == "health-only":
        print("Health check complete. Exiting.")
        return
    
    # Start server
    await run_stdio()

if __name__ == "__main__":
    asyncio.run(main())