"""
Test MCP Client for AIezzy
Tests the MCP server integration with LangChain
"""

import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

async def test_mcp_server():
    """Test the AIezzy MCP server"""

    print(">> Starting MCP client test...\n")

    # Configure MCP client to connect to AIezzy server
    client = MultiServerMCPClient({
        "aiezzy": {
            "command": "python",
            "args": ["mcp_server.py"],
            "transport": "stdio"
        }
    })

    print(">> Connecting to AIezzy MCP server...")

    # Get available tools from MCP server
    try:
        tools = await client.get_tools()
        print(f">> Connected! Found {len(tools)} tools:\n")

        for tool in tools:
            print(f"   - {tool.name}: {tool.description[:80]}...")

        print("\n" + "="*60)
        print(">> Creating LangGraph agent with MCP tools...")

        # Create a ReAct agent with MCP tools
        model = ChatOpenAI(model="gpt-4o", temperature=0)
        agent = create_react_agent(model, tools)

        print(">> Agent created successfully!")
        print("="*60 + "\n")

        # Test 1: Text processing
        print("TEST 1: Text Processing")
        print("-" * 60)
        test_text = "hello world from aiezzy mcp server"
        result = await agent.ainvoke({
            "messages": [{"role": "user", "content": f"Count the words in this text: {test_text}"}]
        })
        print(f"Result: {result['messages'][-1].content}\n")

        # Test 2: Password generation
        print("TEST 2: Password Generation")
        print("-" * 60)
        result = await agent.ainvoke({
            "messages": [{"role": "user", "content": "Generate a 20-character secure password"}]
        })
        print(f"Result: {result['messages'][-1].content}\n")

        # Test 3: Web search
        print("TEST 3: Web Search")
        print("-" * 60)
        result = await agent.ainvoke({
            "messages": [{"role": "user", "content": "Search for latest AI news"}]
        })
        print(f"Result: {result['messages'][-1].content[:300]}...\n")

        print("="*60)
        print(">> All MCP tests completed successfully!")
        print("="*60)

    except Exception as e:
        print(f">> Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_server())
