from typing import List, Dict, Any
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from aiintime_agent.config import get_config
from google.adk.tools import FunctionTool

# Load backend servers
gateway_settings = get_config().gateway
BACKEND_SERVERS = gateway_settings.backend_servers

# ---------------------------
# Helper functions
# ---------------------------
async def _get_server_metadata(name: str, endpoint: str) -> Dict[str, Any]:
    async with streamable_http_client(url=endpoint) as (r, w, _):
        async with ClientSession(r, w) as session:
            init = await session.initialize()
            return {
                "server_name": name,
                "server_description": init.instructions or init.serverInfo.version
            }

async def _list_tools(endpoint: str) -> List[dict]:
    async with streamable_http_client(url=endpoint) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            tools = await session.list_tools()
            return [{"tool_name": t.name, "tool_description": t.description} for t in tools.tools]

async def _describe_tool(endpoint: str, tool_name: str) -> Dict[str, Any]:
    async with streamable_http_client(url=endpoint) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            tools = await session.list_tools()
            for t in tools.tools:
                if t.name == tool_name:
                    return t.model_dump()
            raise ValueError(f"Tool '{tool_name}' not found")

async def _call_tool(endpoint: str, tool_name: str, args: Dict[str, Any]) -> Any:
    async with streamable_http_client(url=endpoint) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            return await session.call_tool(tool_name, arguments=args)

# ---------------------------
# Gateway Tools
# ---------------------------
async def list_mcp_servers() -> List[dict]:
    """List all backend MCP servers."""
    return [
        await _get_server_metadata(name, endpoint)
        for name, endpoint in BACKEND_SERVERS.items()
    ]

async def list_mcp_tools(server_name: str) -> List[dict]:
    """
    List all tools for a specific MCP server.

    args:
        server_name: Name of the MCP server
    """
    endpoint = BACKEND_SERVERS.get(server_name)
    if not endpoint:
        raise ValueError(f"Unknown server: {server_name}")
    return await _list_tools(endpoint)

async def describe_mcp_tool(server_name: str, api_name: str) -> Dict[str, Any]:
    """
    Describe a specific tool for an MCP server.

    args:
        server_name: Name of the MCP server
        api_name: Name of the tool
    """
    endpoint = BACKEND_SERVERS.get(server_name)
    if not endpoint:
        raise ValueError(f"Unknown server: {server_name}")
    return await _describe_tool(endpoint, api_name)

async def execute_mcp_tool(server_name: str, api_name: str, args: Dict[str, Any]) -> Any:
    """
    Execute a tool on a given MCP server.

    args:
        server_name: Name of the MCP server
        api_name: Name of the tool
        args: Arguments for the tool
    """
    endpoint = BACKEND_SERVERS.get(server_name)
    if not endpoint:
        raise ValueError(f"Unknown server: {server_name}")
    return await _call_tool(endpoint, api_name, args)

async def send_response_to_master_agent(response: str) -> Dict[str, Any]:
    """
    Send response to master agent.

    args:
        response: Response to send to master agent
    """
    print(response)
    return {"message": "Response sent to master agent"}

tools = [
    FunctionTool(func=list_mcp_servers),
    FunctionTool(func=list_mcp_tools),
    FunctionTool(func=describe_mcp_tool),
    FunctionTool(func=execute_mcp_tool),
    FunctionTool(func=send_response_to_master_agent),
]    