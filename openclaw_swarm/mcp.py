"""
OpenClaw Swarm - MCP (Model Context Protocol) Support
Compatible with Claude Code MCP protocol
"""

import inspect
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class MCPMessageType(Enum):
    """MCP message types"""

    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"


@dataclass
class MCPTool:
    """MCP Tool definition"""

    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Optional[Callable] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


@dataclass
class MCPResource:
    """MCP Resource definition"""

    uri: str
    name: str
    description: str
    mime_type: str = "text/plain"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }


@dataclass
class MCPPrompt:
    """MCP Prompt template"""

    name: str
    description: str
    arguments: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "arguments": self.arguments,
        }


class MCPServer:
    """MCP Server implementation for OpenClaw Swarm"""

    def __init__(self, name: str = "openclaw-swarm", version: str = "0.6.0"):
        self.name = name
        self.version = version
        self.tools: Dict[str, MCPTool] = {}
        self.resources: Dict[str, MCPResource] = {}
        self.prompts: Dict[str, MCPPrompt] = {}
        self._request_handlers: Dict[str, Callable] = {}

        # Register default handlers
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default MCP request handlers"""
        self._request_handlers["initialize"] = self._handle_initialize
        self._request_handlers["tools/list"] = self._handle_tools_list
        self._request_handlers["tools/call"] = self._handle_tools_call
        self._request_handlers["resources/list"] = self._handle_resources_list
        self._request_handlers["resources/read"] = self._handle_resources_read
        self._request_handlers["prompts/list"] = self._handle_prompts_list
        self._request_handlers["prompts/get"] = self._handle_prompts_get

    def register_tool(self, tool: MCPTool):
        """Register a tool"""
        self.tools[tool.name] = tool

    def register_resource(self, resource: MCPResource):
        """Register a resource"""
        self.resources[resource.uri] = resource

    def register_prompt(self, prompt: MCPPrompt):
        """Register a prompt"""
        self.prompts[prompt.name] = prompt

    # Request Handlers
    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request"""
        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": self.name, "version": self.version},
            "capabilities": {
                "tools": {"listChanged": True},
                "resources": {"subscribe": True, "listChanged": True},
                "prompts": {"listChanged": True},
            },
        }

    async def _handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request"""
        return {"tools": [tool.to_dict() for tool in self.tools.values()]}

    async def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name not in self.tools:
            return {"error": f"Tool not found: {tool_name}"}

        tool = self.tools[tool_name]

        if tool.handler:
            try:
                result = (
                    await tool.handler(**arguments)
                    if inspect.iscoroutinefunction(tool.handler)
                    else tool.handler(**arguments)
                )
                return {"content": [{"type": "text", "text": str(result)}]}
            except Exception as e:
                return {"error": str(e)}

        return {"error": "Tool handler not implemented"}

    async def _handle_resources_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/list request"""
        return {
            "resources": [resource.to_dict() for resource in self.resources.values()]
        }

    async def _handle_resources_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/read request"""
        uri = params.get("uri")

        if uri not in self.resources:
            return {"error": f"Resource not found: {uri}"}

        # Return resource content (implementation specific)
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": self.resources[uri].mime_type,
                    "text": f"Content of {uri}",
                }
            ]
        }

    async def _handle_prompts_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/list request"""
        return {"prompts": [prompt.to_dict() for prompt in self.prompts.values()]}

    async def _handle_prompts_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/get request"""
        name = params.get("name")
        params.get("arguments", {})

        if name not in self.prompts:
            return {"error": f"Prompt not found: {name}"}

        prompt = self.prompts[name]

        # Return prompt template with arguments
        return {
            "description": prompt.description,
            "messages": [
                {"role": "user", "content": {"type": "text", "text": f"Prompt: {name}"}}
            ],
        }

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP request"""
        method = request.get("method")
        params = request.get("params", {})

        if method not in self._request_handlers:
            return {"error": f"Unknown method: {method}"}

        handler = self._request_handlers[method]

        try:
            result = await handler(params)
            return {"result": result}
        except Exception as e:
            return {"error": str(e)}

    def create_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: Callable = None,
    ) -> MCPTool:
        """Create and register a tool"""
        tool = MCPTool(
            name=name,
            description=description,
            input_schema=input_schema,
            handler=handler,
        )
        self.register_tool(tool)
        return tool

    def create_resource(
        self, uri: str, name: str, description: str, mime_type: str = "text/plain"
    ) -> MCPResource:
        """Create and register a resource"""
        resource = MCPResource(
            uri=uri, name=name, description=description, mime_type=mime_type
        )
        self.register_resource(resource)
        return resource

    def create_prompt(
        self, name: str, description: str, arguments: List[Dict[str, Any]] = None
    ) -> MCPPrompt:
        """Create and register a prompt"""
        prompt = MCPPrompt(
            name=name, description=description, arguments=arguments or []
        )
        self.register_prompt(prompt)
        return prompt


class MCPClient:
    """MCP Client for connecting to other MCP servers"""

    def __init__(self):
        self.servers: Dict[str, Dict[str, Any]] = {}

    async def connect(
        self,
        server_name: str,
        transport: str = "stdio",
        command: str = None,
        args: List[str] = None,
    ):
        """Connect to an MCP server"""
        self.servers[server_name] = {
            "transport": transport,
            "command": command,
            "args": args or [],
            "connected": False,
        }

        # In a real implementation, this would spawn the server process
        # and establish communication
        return {"status": "connected", "server": server_name}

    async def list_tools(self, server_name: str) -> List[MCPTool]:
        """List tools from a connected server"""
        if server_name not in self.servers:
            return []

        # In a real implementation, this would send a tools/list request
        return []

    async def call_tool(
        self, server_name: str, tool_name: str, arguments: Dict[str, Any]
    ) -> Any:
        """Call a tool on a connected server"""
        if server_name not in self.servers:
            raise ValueError(f"Server not connected: {server_name}")

        # In a real implementation, this would send a tools/call request
        return None


# Pre-defined MCP tools for OpenClaw Swarm
def create_swarm_tools(server: MCPServer):
    """Create OpenClaw Swarm MCP tools"""

    # Router tool
    server.create_tool(
        name="router_call",
        description="Call the OpenClaw Swarm router to process a prompt",
        input_schema={
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "The prompt to process"},
                "task_type": {
                    "type": "string",
                    "enum": ["coding", "reasoning", "chat", "general"],
                    "description": "Task type",
                },
            },
            "required": ["prompt"],
        },
    )

    # Memory tool
    server.create_tool(
        name="memory_search",
        description="Search OpenClaw Swarm memory",
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
    )

    # Swarm tool
    server.create_tool(
        name="swarm_run",
        description="Run a swarm task",
        input_schema={
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Task description"},
                "max_workers": {
                    "type": "integer",
                    "description": "Max parallel workers",
                    "default": 3,
                },
            },
            "required": ["task"],
        },
    )

    # Experience tool
    server.create_tool(
        name="experience_get_advice",
        description="Get advice from past experiences",
        input_schema={
            "type": "object",
            "properties": {"task_type": {"type": "string", "description": "Task type"}},
            "required": ["task_type"],
        },
    )

    # Anonymizer tool
    server.create_tool(
        name="anonymize_text",
        description="Anonymize PII in text",
        input_schema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to anonymize"}
            },
            "required": ["text"],
        },
    )

    # Web search tool
    server.create_tool(
        name="web_search",
        description="Search the web",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {
                    "type": "integer",
                    "description": "Max results",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    )


def create_swarm_resources(server: MCPServer):
    """Create OpenClaw Swarm MCP resources"""

    server.create_resource(
        uri="swarm://config/models",
        name="Model Configuration",
        description="Current model routing configuration",
        mime_type="application/json",
    )

    server.create_resource(
        uri="swarm://config/agents",
        name="Agent Configuration",
        description="Available agents and their capabilities",
        mime_type="application/json",
    )

    server.create_resource(
        uri="swarm://memory/stats",
        name="Memory Statistics",
        description="Current memory usage statistics",
        mime_type="application/json",
    )

    server.create_resource(
        uri="swarm://experience/lessons",
        name="Learned Lessons",
        description="Lessons learned from past tasks",
        mime_type="application/json",
    )


def create_swarm_prompts(server: MCPServer):
    """Create OpenClaw Swarm MCP prompts"""

    server.create_prompt(
        name="code_generation",
        description="Generate code using OpenClaw Swarm",
        arguments=[
            {
                "name": "language",
                "description": "Programming language",
                "required": True,
            },
            {"name": "task", "description": "Task description", "required": True},
        ],
    )

    server.create_prompt(
        name="code_review",
        description="Review code using OpenClaw Swarm",
        arguments=[{"name": "code", "description": "Code to review", "required": True}],
    )

    server.create_prompt(
        name="task_planning",
        description="Plan a complex task",
        arguments=[
            {"name": "task", "description": "Task description", "required": True}
        ],
    )


# Convenience function to create a fully configured MCP server
def create_mcp_server() -> MCPServer:
    """Create a fully configured MCP server for OpenClaw Swarm"""
    server = MCPServer()

    # Register tools
    create_swarm_tools(server)

    # Register resources
    create_swarm_resources(server)

    # Register prompts
    create_swarm_prompts(server)

    return server
