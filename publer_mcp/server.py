"""FastMCP server entry point for Publer integration.

This file should not be modified. All logic belongs in the tools/ directory.
"""

from contextlib import AsyncExitStack

import uvicorn
from mcp.server import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from publer_mcp.registry import register_tools
from publer_mcp.settings import settings

# Initialize MCP server
mcp = FastMCP(
    name="publer-mcp",
    host=settings.host,
    port=settings.port,
    # Always mount at root for consistency
    streamable_http_path="/",
    debug=True,
    log_level=settings.log_level,
    stateless_http=True,  # Avoids worker/mounting issues
)

# Register all tools from registry.py
register_tools(mcp)

# Streamable HTTP app
mcp_app = mcp.streamable_http_app()


# Lifespan integration so MCP startup/shutdown hooks work
def create_lifespan():
    async def lifespan(app):
        async with AsyncExitStack() as stack:
            await stack.enter_async_context(mcp_app.router.lifespan_context(app))
            yield

    return lifespan


# Health check endpoint
async def health_check(request):
    return JSONResponse({"status": "healthy", "service": "publer-mcp"})


# Starlette app with routes
app = Starlette(
    debug=False,
    lifespan=create_lifespan(),
    routes=[
        Route("/health", health_check, methods=["GET"]),
        Mount("/mcp", mcp_app),
    ],
)


# Local/dev entrypoint
def main():
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
