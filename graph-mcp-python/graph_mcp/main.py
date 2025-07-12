#!/usr/bin/env python3
"""Microsoft Graph MCP Server - Main entry point."""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource, 
    Tool, 
    TextContent, 
    ImageContent, 
    EmbeddedResource
)

from .config import Settings
from .services.graph_service import GraphService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('azure_cli_mcp.log'),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

# Create server instance
server = Server("microsoft-graph-mcp")

# Initialize settings and service
settings = Settings()
graph_service = GraphService(settings)

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools."""
    return [
        Tool(
            name="graph_command",
            description="Execute Microsoft Graph API commands. Supports GET, POST, PUT, PATCH, DELETE operations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Graph API endpoint (e.g., 'users', 'me', 'groups', 'devices')"
                    },
                    "method": {
                        "type": "string", 
                        "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                        "default": "GET",
                        "description": "HTTP method to use"
                    },
                    "data": {
                        "type": "object",
                        "description": "Request body data (for POST, PUT, PATCH operations)"
                    },
                    "client_secret": {
                        "type": "string",
                        "description": "Azure AD client secret (optional, for authenticated operations)"
                    }
                },
                "required": ["command"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls."""
    if name != "graph_command":
        raise ValueError(f"Unknown tool: {name}")
    
    command = arguments.get("command", "")
    method = arguments.get("method", "GET")
    data = arguments.get("data")
    client_secret = arguments.get("client_secret")
    
    logger.info(f"Executing Graph command: {method} {command}")
    
    try:
        result = await graph_service.execute_command(command, method, data, client_secret)
        
        # Format the response
        if result.get("success"):
            response_text = f"✅ **Success** ({method} {command})\n\n"
            if result.get("data"):
                response_text += f"```json\n{json.dumps(result['data'], indent=2)}\n```"
            else:
                response_text += "Operation completed successfully."
        else:
            response_text = f"❌ **Error** ({method} {command})\n\n"
            response_text += f"**Error:** {result.get('error', 'Unknown error')}\n\n"
            
            if result.get("auth_required") and result.get("instructions"):
                response_text += f"**Instructions:**\n{result['instructions']}\n\n"
            
            if result.get("error_details"):
                response_text += f"**Details:**\n```json\n{json.dumps(result['error_details'], indent=2)}\n```"
        
        return [TextContent(type="text", text=response_text)]
        
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        error_text = f"❌ **Tool Execution Failed**\n\n**Error:** {str(e)}"
        return [TextContent(type="text", text=error_text)]

@server.list_resources()
async def list_resources() -> List[Resource]:
    """List available resources."""
    return [
        Resource(
            uri="graph://help",
            name="Microsoft Graph Help",
            description="Help and examples for using Microsoft Graph API",
            mimeType="text/plain"
        )
    ]

@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read a resource."""
    if uri == "graph://help":
        return """
# Microsoft Graph MCP Server Help

This server provides access to Microsoft Graph API endpoints through MCP tools.

## Authentication

The server supports two authentication modes:

1. **Device Code Flow (Recommended for read-only operations)**
   - No client secret required
   - Opens browser for authentication
   - Suitable for user-delegated permissions

2. **Client Secret Flow (For application permissions)**
   - Requires client secret
   - Suitable for automated operations
   - Pass client_secret parameter to the tool

## Configuration

Set these environment variables:
- `AZURE_CLIENT_ID`: Your Azure AD application client ID
- `AZURE_TENANT_ID`: Your Azure AD tenant ID  
- `AZURE_CLIENT_SECRET`: Your client secret (optional, for app permissions)

## Examples

### Get current user info
```
graph_command(command="me")
```

### List all users
```
graph_command(command="users")
```

### Get specific user
```
graph_command(command="users/user@domain.com")
```

### Create a user (requires client secret)
```
graph_command(
    command="users", 
    method="POST",
    data={
        "accountEnabled": true,
        "displayName": "John Doe",
        "mailNickname": "johndoe",
        "userPrincipalName": "johndoe@yourdomain.com",
        "passwordProfile": {
            "forceChangePasswordNextSignIn": true,
            "password": "TempPassword123!"
        }
    },
    client_secret="your-client-secret"
)
```

### Update user
```
graph_command(
    command="users/user@domain.com",
    method="PATCH", 
    data={"jobTitle": "Senior Developer"}
)
```

### Delete user
```
graph_command(
    command="users/user@domain.com",
    method="DELETE"
)
```

## Common Endpoints

- `me` - Current user info
- `users` - All users
- `groups` - All groups  
- `devices` - All devices
- `applications` - Applications
- `servicePrincipals` - Service principals
- `directoryRoles` - Directory roles
- `organization` - Organization info

For more endpoints, see: https://docs.microsoft.com/en-us/graph/api/overview
"""
    
    raise ValueError(f"Unknown resource: {uri}")

async def main():
    """Main entry point."""
    logger.info("Starting Microsoft Graph MCP Server")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main()) 