"""
Example: MCP (Model Context Protocol) Server
=============================================

This example shows how to create an MCP server.
"""

import asyncio
from openclaw_swarm import create_mcp_server


async def main():
    print("=" * 60)
    print("OpenClaw Swarm - MCP Server Example")
    print("=" * 60)

    # 1. Create MCP Server
    print("\n1. Create MCP Server")
    print("-" * 40)

    server = create_mcp_server()

    print(f"Server name: {server.name}")
    print(f"Server version: {server.version}")
    print(f"Tools registered: {len(server.tools)}")
    print(f"Resources registered: {len(server.resources)}")
    print(f"Prompts registered: {len(server.prompts)}")

    # 2. List Available Tools
    print("\n2. Available Tools")
    print("-" * 40)

    for tool_name, tool in server.tools.items():
        print(f"  - {tool_name}: {tool.description}")

    # 3. List Available Resources
    print("\n3. Available Resources")
    print("-" * 40)

    for uri, resource in server.resources.items():
        print(f"  - {uri}: {resource.name}")

    # 4. List Available Prompts
    print("\n4. Available Prompts")
    print("-" * 40)

    for prompt_name, prompt in server.prompts.items():
        print(f"  - {prompt_name}: {prompt.description}")

    # 5. Handle Initialize Request
    print("\n5. Handle Initialize Request")
    print("-" * 40)

    result = await server.handle_request({"method": "initialize", "params": {}})

    print(f"Protocol version: {result['result']['protocolVersion']}")
    print(f"Server info: {result['result']['serverInfo']}")
    print(f"Capabilities: {list(result['result']['capabilities'].keys())}")

    # 6. Handle Tools List Request
    print("\n6. Handle Tools List Request")
    print("-" * 40)

    result = await server.handle_request({"method": "tools/list", "params": {}})

    print(f"Tools count: {len(result['result']['tools'])}")
    for tool in result["result"]["tools"][:3]:
        print(f"  - {tool['name']}")

    # 7. Register Custom Tool
    print("\n7. Register Custom Tool")
    print("-" * 40)

    async def custom_handler(query: str, limit: int = 5):
        """Custom tool handler"""
        return f"Processed: {query} (limit: {limit})"

    server.create_tool(
        name="custom_search",
        description="Custom search tool",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {
                    "type": "integer",
                    "description": "Max results",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
        handler=custom_handler,
    )

    print("Custom tool registered: custom_search")

    # 8. Handle Tools Call Request
    print("\n8. Handle Tools Call Request")
    print("-" * 40)

    result = await server.handle_request(
        {
            "method": "tools/call",
            "params": {
                "name": "custom_search",
                "arguments": {"query": "test", "limit": 3},
            },
        }
    )

    if "result" in result:
        print(f"Result: {result['result']['content'][0]['text']}")
    else:
        print(f"Error: {result.get('error')}")

    # 9. Create Custom Resource
    print("\n9. Create Custom Resource")
    print("-" * 40)

    server.create_resource(
        uri="swarm://custom/data",
        name="Custom Data",
        description="Custom data resource",
        mime_type="application/json",
    )

    print("Custom resource registered: swarm://custom/data")

    # 10. Create Custom Prompt
    print("\n10. Create Custom Prompt")
    print("-" * 40)

    server.create_prompt(
        name="custom_prompt",
        description="Custom prompt template",
        arguments=[
            {"name": "topic", "description": "Topic to discuss", "required": True},
            {"name": "style", "description": "Writing style", "required": False},
        ],
    )

    print("Custom prompt registered: custom_prompt")

    # 11. Get Final Stats
    print("\n11. Final Statistics")
    print("-" * 40)

    print(f"Total tools: {len(server.tools)}")
    print(f"Total resources: {len(server.resources)}")
    print(f"Total prompts: {len(server.prompts)}")

    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
