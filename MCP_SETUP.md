# AIezzy MCP Server Setup Guide

## Overview

AIezzy now includes a **Model Context Protocol (MCP) server** that exposes AI capabilities as standardized tools. This allows external applications, IDEs, and AI agents to leverage AIezzy's powerful features through a unified interface.

## What is MCP?

The **Model Context Protocol (MCP)** is an open standard developed by Anthropic that connects Large Language Models (LLMs) with external tools and data sources. Think of it as "USB-C for AI" - a universal interface for AI integrations.

## Features

The AIezzy MCP server exposes **10 powerful tools**:

### Image Tools
- **generate_image**: Create images from text prompts using FAL AI nano-banana
- **edit_image**: Modify existing images with AI-powered editing

### Video Tools
- **generate_video_from_text**: Create videos from text descriptions
- **generate_video_from_image**: Animate images into videos

### Search Tools
- **search_web**: Real-time web search using Tavily AI

### Text Processing Tools
- **count_words**: Analyze text statistics (words, characters, sentences, paragraphs)
- **convert_text_case**: Convert text to different cases (uppercase, lowercase, title, etc.)
- **generate_password**: Create secure random passwords

### QR Code & Barcode Tools
- **create_qr_code**: Generate QR codes for URLs, text, or data
- **create_barcode**: Create barcodes in various formats (Code128, EAN13, etc.)

## Installation

### 1. Install Dependencies

```bash
pip install langchain-mcp-adapters mcp
```

Or install from requirements.txt:

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Ensure your `.env` file contains the necessary API keys:

```env
OPENAI_API_KEY=sk-...        # For GPT-4o
FAL_KEY=your_fal_key_here    # For image/video generation
TAVILY_API_KEY=your_key      # For web search
```

## Usage

### Running the MCP Server Standalone

Start the MCP server directly:

```bash
python mcp_server.py
```

The server runs on **stdio transport** for local communication.

### Connecting from LangChain/LangGraph

Use the server with LangChain agents:

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

# Configure MCP client
client = MultiServerMCPClient({
    "aiezzy": {
        "command": "python",
        "args": ["mcp_server.py"],
        "transport": "stdio"
    }
})

# Get available tools
tools = await client.get_tools()

# Create agent with MCP tools
model = ChatOpenAI(model="gpt-4o", temperature=0)
agent = create_react_agent(model, tools)

# Use the agent
result = await agent.ainvoke({
    "messages": [{"role": "user", "content": "Generate a QR code for https://aiezzy.com"}]
})
```

### Using with Claude Code

Add AIezzy MCP server to your Claude Code configuration:

**Location**: `~/.claude/claude_desktop_config.json` (macOS/Linux) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows)

```json
{
  "mcpServers": {
    "aiezzy": {
      "command": "python",
      "args": ["C:\\Users\\User\\Desktop\\aiezzy-ai-chatbot-master\\mcp_server.py"],
      "transport": "stdio"
    }
  }
}
```

Then restart Claude Code to load the AIezzy tools.

## Testing

Run the included test suite:

```bash
python test_mcp_client.py
```

Expected output:

```
>> Starting MCP client test...
>> Connecting to AIezzy MCP server...
>> Connected! Found 10 tools:

   - generate_image
   - edit_image
   - generate_video_from_text
   - generate_video_from_image
   - search_web
   - count_words
   - convert_text_case
   - generate_password
   - create_qr_code
   - create_barcode

TEST 1: Text Processing
------------------------------------------------------------
Result: The text contains 6 words...

TEST 2: Password Generation
------------------------------------------------------------
Result: Generated password: YWk#5zGt&mE1:0nua&;a

>> All MCP tests completed successfully!
```

## Architecture

### Transport Protocol

- **stdio**: Server communicates via standard input/output
- Best for local tools and simple setups
- Process is launched as a subprocess by the client

### Tool Schema

Each tool is automatically exposed with:
- **Name**: Function name
- **Description**: Extracted from docstring
- **Parameters**: Type-safe argument schema
- **Returns**: Result from tool execution

### File Storage

- Generated images: `assets/`
- Generated videos: `videos/`
- QR codes/barcodes: `assets/`

## Example Use Cases

### 1. Generate Image and Create QR Code

```python
result = await agent.ainvoke({
    "messages": [{
        "role": "user",
        "content": "Generate an image of a mountain landscape and create a QR code for aiezzy.com"
    }]
})
```

### 2. Web Search and Generate Summary

```python
result = await agent.ainvoke({
    "messages": [{
        "role": "user",
        "content": "Search for latest AI news and summarize it"
    }]
})
```

### 3. Create Secure Password

```python
result = await agent.ainvoke({
    "messages": [{
        "role": "user",
        "content": "Generate a 32-character password with all character types"
    }]
})
```

## Troubleshooting

### Server Not Starting

- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check that Python 3.10+ is being used
- Verify API keys are set in `.env` file

### Connection Issues

- Make sure the path to `mcp_server.py` is correct in your configuration
- Check that the server has permission to write to `assets/` and `videos/` directories
- Verify firewall/antivirus isn't blocking Python subprocess communication

### Tool Execution Errors

- **Image/Video generation**: Verify FAL_KEY is valid
- **Web search**: Verify TAVILY_API_KEY is configured
- **File not found**: Check file paths are absolute, not relative

## Advanced Configuration

### Adding Custom Tools

To add new tools to the MCP server:

1. Define a new function with `@mcp.tool()` decorator
2. Add clear docstring with Args and Returns sections
3. Implement the tool logic
4. Restart the MCP server

Example:

```python
@mcp.tool()
def custom_tool(param1: str, param2: int) -> str:
    """
    Brief description of what this tool does.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value
    """
    # Tool implementation
    return f"Result: {param1} {param2}"
```

### Using Different Transports

MCP supports multiple transport protocols:

- **stdio**: For local processes (current implementation)
- **HTTP**: For remote server access
- **WebSocket**: For real-time bidirectional communication

To use HTTP transport:

```python
if __name__ == "__main__":
    mcp.run(transport="http", port=8000)
```

## Resources

- **MCP Documentation**: https://docs.langchain.com/mcp
- **LangChain MCP Adapters**: https://github.com/langchain-ai/langchain-mcp
- **AIezzy GitHub**: https://github.com/yatendra3192/aiezzy-ai-chatbot
- **MCP Specification**: https://spec.modelcontextprotocol.io/

## License

This MCP server implementation is part of the AIezzy project and follows the same license terms.

---

**Last Updated**: October 27, 2025
**Status**: Production Ready ✅
**Version**: 1.0.0
