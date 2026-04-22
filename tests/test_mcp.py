"""
Tests for MCP Support
"""

import pytest

from openclaw_swarm.mcp import (
    MCPClient,
    MCPMessageType,
    MCPPrompt,
    MCPResource,
    MCPServer,
    MCPTool,
    create_mcp_server,
    create_swarm_prompts,
    create_swarm_resources,
    create_swarm_tools,
)


class TestMCPMessageType:
    """Test MCPMessageType enum"""

    def test_message_types_exist(self):
        """Test all message types exist"""
        assert MCPMessageType.REQUEST.value == "request"
        assert MCPMessageType.RESPONSE.value == "response"
        assert MCPMessageType.NOTIFICATION.value == "notification"


class TestMCPTool:
    """Test MCPTool dataclass"""

    def test_tool_creation(self):
        """Test creating a tool"""
        tool = MCPTool(
            name="test_tool", description="A test tool", input_schema={"type": "object"}
        )

        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.input_schema == {"type": "object"}
        assert tool.handler is None

    def test_tool_to_dict(self):
        """Test converting tool to dict"""
        tool = MCPTool(
            name="test_tool",
            description="A test tool",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
            },
        )

        result = tool.to_dict()

        assert result["name"] == "test_tool"
        assert result["description"] == "A test tool"
        assert "inputSchema" in result

    def test_tool_with_handler(self):
        """Test tool with handler"""

        def handler(query: str):
            return f"Result: {query}"

        tool = MCPTool(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object"},
            handler=handler,
        )

        assert tool.handler is not None
        result = tool.handler(query="test")
        assert result == "Result: test"


class TestMCPResource:
    """Test MCPResource dataclass"""

    def test_resource_creation(self):
        """Test creating a resource"""
        resource = MCPResource(
            uri="test://resource", name="Test Resource", description="A test resource"
        )

        assert resource.uri == "test://resource"
        assert resource.name == "Test Resource"
        assert resource.mime_type == "text/plain"

    def test_resource_to_dict(self):
        """Test converting resource to dict"""
        resource = MCPResource(
            uri="test://resource",
            name="Test Resource",
            description="A test resource",
            mime_type="application/json",
        )

        result = resource.to_dict()

        assert result["uri"] == "test://resource"
        assert result["mimeType"] == "application/json"


class TestMCPPrompt:
    """Test MCPPrompt dataclass"""

    def test_prompt_creation(self):
        """Test creating a prompt"""
        prompt = MCPPrompt(name="test_prompt", description="A test prompt")

        assert prompt.name == "test_prompt"
        assert prompt.arguments == []

    def test_prompt_with_arguments(self):
        """Test prompt with arguments"""
        prompt = MCPPrompt(
            name="test_prompt",
            description="A test prompt",
            arguments=[
                {"name": "arg1", "type": "string"},
                {"name": "arg2", "type": "integer"},
            ],
        )

        assert len(prompt.arguments) == 2
        assert prompt.arguments[0]["name"] == "arg1"

    def test_prompt_to_dict(self):
        """Test converting prompt to dict"""
        prompt = MCPPrompt(
            name="test_prompt",
            description="A test prompt",
            arguments=[{"name": "arg1", "required": True}],
        )

        result = prompt.to_dict()

        assert result["name"] == "test_prompt"
        assert result["arguments"] == [{"name": "arg1", "required": True}]


class TestMCPServer:
    """Test MCPServer class"""

    def test_server_initialization(self):
        """Test server initialization"""
        server = MCPServer()

        assert server.name == "openclaw-swarm"
        assert server.version == "0.6.0"
        assert len(server.tools) == 0
        assert len(server.resources) == 0
        assert len(server.prompts) == 0

    def test_server_with_custom_name(self):
        """Test server with custom name"""
        server = MCPServer(name="custom-server", version="1.0.0")

        assert server.name == "custom-server"
        assert server.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_handle_initialize(self):
        """Test initialize handler"""
        server = MCPServer()

        result = await server._handle_initialize({})

        assert result["protocolVersion"] == "2024-11-05"
        assert result["serverInfo"]["name"] == "openclaw-swarm"
        assert "tools" in result["capabilities"]

    @pytest.mark.asyncio
    async def test_handle_tools_list(self):
        """Test tools/list handler"""
        server = MCPServer()
        server.create_tool("test_tool", "Test tool", {"type": "object"})

        result = await server._handle_tools_list({})

        assert "tools" in result
        assert len(result["tools"]) == 1
        assert result["tools"][0]["name"] == "test_tool"

    @pytest.mark.asyncio
    async def test_handle_resources_list(self):
        """Test resources/list handler"""
        server = MCPServer()
        server.create_resource("test://resource", "Test", "Test resource")

        result = await server._handle_resources_list({})

        assert "resources" in result
        assert len(result["resources"]) == 1

    @pytest.mark.asyncio
    async def test_handle_prompts_list(self):
        """Test prompts/list handler"""
        server = MCPServer()
        server.create_prompt("test_prompt", "Test prompt")

        result = await server._handle_prompts_list({})

        assert "prompts" in result
        assert len(result["prompts"]) == 1

    def test_register_tool(self):
        """Test registering a tool"""
        server = MCPServer()
        tool = MCPTool(name="test", description="Test", input_schema={})

        server.register_tool(tool)

        assert "test" in server.tools
        assert server.tools["test"] == tool

    def test_register_resource(self):
        """Test registering a resource"""
        server = MCPServer()
        resource = MCPResource(uri="test://res", name="Test", description="Test")

        server.register_resource(resource)

        assert "test://res" in server.resources

    def test_register_prompt(self):
        """Test registering a prompt"""
        server = MCPServer()
        prompt = MCPPrompt(name="test", description="Test")

        server.register_prompt(prompt)

        assert "test" in server.prompts

    def test_create_tool(self):
        """Test create_tool helper"""
        server = MCPServer()

        tool = server.create_tool(
            name="helper_tool",
            description="Helper tool",
            input_schema={"type": "object"},
        )

        assert tool.name == "helper_tool"
        assert "helper_tool" in server.tools

    @pytest.mark.asyncio
    async def test_handle_tools_call(self):
        """Test tools/call handler"""
        server = MCPServer()

        async def handler(query: str):
            return f"Result: {query}"

        server.create_tool(
            name="test_tool", description="Test", input_schema={}, handler=handler
        )

        result = await server._handle_tools_call(
            {"name": "test_tool", "arguments": {"query": "test"}}
        )

        assert "content" in result
        assert "Result: test" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_handle_tools_call_not_found(self):
        """Test tools/call with non-existent tool"""
        server = MCPServer()

        result = await server._handle_tools_call(
            {"name": "nonexistent", "arguments": {}}
        )

        assert "error" in result

    @pytest.mark.asyncio
    async def test_handle_request(self):
        """Test handle_request"""
        server = MCPServer()

        result = await server.handle_request({"method": "initialize", "params": {}})

        assert "result" in result


class TestMCPClient:
    """Test MCPClient class"""

    def test_client_initialization(self):
        """Test client initialization"""
        client = MCPClient()

        assert len(client.servers) == 0

    @pytest.mark.asyncio
    async def test_connect(self):
        """Test connecting to server"""
        client = MCPClient()

        result = await client.connect(
            server_name="test-server", transport="stdio", command="test"
        )

        assert result["status"] == "connected"
        assert "test-server" in client.servers


class TestSwarmMCP:
    """Test OpenClaw Swarm MCP tools"""

    def test_create_swarm_tools(self):
        """Test creating swarm tools"""
        server = MCPServer()
        create_swarm_tools(server)

        assert "router_call" in server.tools
        assert "memory_search" in server.tools
        assert "swarm_run" in server.tools
        assert "experience_get_advice" in server.tools
        assert "anonymize_text" in server.tools
        assert "web_search" in server.tools

    def test_create_swarm_resources(self):
        """Test creating swarm resources"""
        server = MCPServer()
        create_swarm_resources(server)

        assert "swarm://config/models" in server.resources
        assert "swarm://config/agents" in server.resources
        assert "swarm://memory/stats" in server.resources
        assert "swarm://experience/lessons" in server.resources

    def test_create_swarm_prompts(self):
        """Test creating swarm prompts"""
        server = MCPServer()
        create_swarm_prompts(server)

        assert "code_generation" in server.prompts
        assert "code_review" in server.prompts
        assert "task_planning" in server.prompts

    def test_create_mcp_server(self):
        """Test create_mcp_server convenience function"""
        server = create_mcp_server()

        # Check tools
        assert len(server.tools) >= 6

        # Check resources
        assert len(server.resources) >= 4

        # Check prompts
        assert len(server.prompts) >= 3
