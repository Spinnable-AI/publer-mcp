# Publer MCP Server

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

The first comprehensive **Model Context Protocol (MCP) server** for [Publer](https://publer.io), a powerful social media management platform. This integration enables AI assistants like Claude to interact with Publer's API for managing social media posts, accounts, media, and analytics.

## 🌟 Features

### 📱 Account Management
- List all connected social media accounts
- Get detailed account information
- Support for multiple platforms (Facebook, Instagram, Twitter, LinkedIn, Pinterest, YouTube, TikTok, Google Business)

### 📝 Post Management  
- Create and schedule posts across multiple platforms
- List posts with advanced filtering (status, platform, date range)
- Retrieve detailed post information
- Delete or cancel scheduled posts
- Support for text, media, and link sharing

### 🎬 Media Library
- Upload media from URLs to Publer library
- List and search media items
- Get detailed media information and metadata
- Support for photos, videos, and GIFs

### 📊 Analytics
- Retrieve post performance metrics (impressions, reach, engagement)
- Get account-level analytics over date ranges
- Track likes, comments, shares, clicks, and saves
- Multi-platform analytics support

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Publer Business Plan** (required for API access)
- **Publer API Key** and **Workspace ID**

### Installation

#### Option 1: From Source
```bash
git clone https://github.com/Spinnable-AI/publer-mcp.git
cd publer-mcp
pip install -e .
```

#### Option 2: Direct Installation
```bash
pip install git+https://github.com/Spinnable-AI/publer-mcp.git
```

### Configuration

1. **Get your Publer API credentials:**
   - Log into your Publer account (Business plan required)
   - Navigate to Settings → API
   - Generate an API key
   - Copy your Workspace ID

2. **Set environment variables:**
   ```bash
   export PUBLER_API_KEY="your-api-key-here"
   export PUBLER_WORKSPACE_ID="your-workspace-id"
   ```

### Usage with Claude Desktop

Add the following configuration to your Claude Desktop config file:

#### For Stdio Transport (Local Development)
```json
{
  "mcpServers": {
    "publer": {
      "command": "publer-mcp",
      "env": {
        "PUBLER_API_KEY": "your-api-key-here",
        "PUBLER_WORKSPACE_ID": "your-workspace-id"
      }
    }
  }
}
```

#### For Remote/Production (SSE Transport)
```json
{
  "mcpServers": {
    "publer": {
      "url": "https://your-deployed-instance.fly.dev/sse",
      "env": {
        "PUBLER_API_KEY": "your-api-key-here", 
        "PUBLER_WORKSPACE_ID": "your-workspace-id"
      }
    }
  }
}
```

## 🔧 Development

### Local Development Setup

1. **Clone and install:**
   ```bash
   git clone https://github.com/Spinnable-AI/publer-mcp.git
   cd publer-mcp
   pip install -e ".[dev]"
   ```

2. **Set up pre-commit hooks:**
   ```bash
   pre-commit install
   ```

3. **Run tests:**
   ```bash
   pytest
   ```

4. **Run with stdio transport:**
   ```bash
   PUBLER_API_KEY="your-key" PUBLER_WORKSPACE_ID="your-id" python -m publer_mcp.server
   ```

### Testing with MCP Inspector

```bash
# Install MCP Inspector
npm install -g @anthropics/mcp-inspector

# Test the server
PUBLER_API_KEY="your-key" PUBLER_WORKSPACE_ID="your-id" mcp-inspector python -m publer_mcp.server
```

## 🛠️ Available Tools

### Account Tools

| Tool | Description | Required Parameters |
|------|-------------|-------------------|
| `publer_account_list` | List connected social media accounts | - |
| `publer_account_get` | Get account details | `account_id` |

### Post Tools

| Tool | Description | Required Parameters |
|------|-------------|-------------------|
| `publer_post_create` | Create and schedule posts | `content`, `account_ids` |
| `publer_post_list` | List posts with filtering | - |
| `publer_post_get` | Get post details | `post_id` |
| `publer_post_delete` | Delete/cancel posts | `post_id` |

### Media Tools

| Tool | Description | Required Parameters |
|------|-------------|-------------------|
| `publer_media_list` | List media library items | - |
| `publer_media_get` | Get media details | `media_id` |
| `publer_media_upload` | Upload media from URL | `media_url`, `filename` |

### Analytics Tools

| Tool | Description | Required Parameters |
|------|-------------|-------------------|
| `publer_analytics_post` | Get post analytics | `post_id` |
| `publer_analytics_account` | Get account analytics | `account_id`, `start_date`, `end_date` |

## 📋 Examples

### Creating a Social Media Post

```json
{
  "tool": "publer_post_create",
  "arguments": {
    "content": "🚀 Exciting news! We just launched our new MCP integration for Publer!",
    "account_ids": [123, 456],
    "scheduled_at": "2024-12-01T15:30:00Z",
    "link": "https://github.com/Spinnable-AI/publer-mcp"
  }
}
```

### Listing Recent Posts

```json
{
  "tool": "publer_post_list", 
  "arguments": {
    "status": "published",
    "limit": 10
  }
}
```

### Getting Post Analytics

```json
{
  "tool": "publer_analytics_post",
  "arguments": {
    "post_id": 789
  }
}
```

## 🚀 Deployment

### Deploy to Fly.io

1. **Install Fly CLI and authenticate:**
   ```bash
   flyctl auth login
   ```

2. **Deploy:**
   ```bash
   flyctl launch
   flyctl secrets set PUBLER_API_KEY="your-api-key"
   flyctl secrets set PUBLER_WORKSPACE_ID="your-workspace-id"
   flyctl deploy
   ```

3. **Your MCP server will be available at:**
   ```
   https://your-app-name.fly.dev/sse
   ```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `PUBLER_API_KEY` | Your Publer API key | ✅ |
| `PUBLER_WORKSPACE_ID` | Your Publer workspace ID | ✅ |
| `TRANSPORT` | Transport mode (`stdio` or `sse`) | ❌ (default: `stdio`) |
| `PORT` | Port for SSE transport | ❌ (default: `8000`) |

## 🔒 Security

- **API Key Security**: Never commit API keys to version control
- **Environment Variables**: Use secure environment variable management
- **HTTPS**: All API communications use HTTPS
- **Rate Limiting**: Built-in rate limiting and exponential backoff
- **Input Validation**: Comprehensive input validation and sanitization

## 🤝 Contributing

We welcome contributions! This is the first comprehensive Publer MCP integration, and we're excited to build it together.

### Development Workflow

1. **Fork the repository**
2. **Create a feature branch:** `git checkout -b feature/amazing-feature`
3. **Make your changes and add tests**
4. **Run the test suite:** `pytest`
5. **Run type checking:** `mypy src/`
6. **Format code:** `black src/ tests/`
7. **Commit changes:** `git commit -m 'Add amazing feature'`
8. **Push to branch:** `git push origin feature/amazing-feature`
9. **Open a Pull Request**

### Code Standards

- **Python 3.11+** with type hints
- **Black** for code formatting
- **pytest** for testing (aim for >90% coverage)
- **mypy** for type checking
- **Comprehensive docstrings** for all public functions

## 🆘 Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify your API key and workspace ID are correct
   - Ensure you have a Publer Business plan
   - Check that your API key has the necessary permissions

2. **Rate Limiting**
   - The server automatically handles rate limiting with exponential backoff
   - If you hit limits frequently, consider reducing request frequency

3. **Network Issues**
   - Check your internet connection
   - Verify Publer's API is operational at [status.publer.io](https://status.publer.io)

4. **Invalid Data**
   - Review the tool schemas for required parameters
   - Ensure date formats use ISO 8601 standard
   - Verify account IDs and media IDs exist

### Debug Mode

Run with debug logging:
```bash
PYTHONPATH=. PUBLER_API_KEY="your-key" PUBLER_WORKSPACE_ID="your-id" python -m publer_mcp.server --log-level DEBUG
```

### Getting Help

- **Issues**: [GitHub Issues](https://github.com/Spinnable-AI/publer-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Spinnable-AI/publer-mcp/discussions)
- **Email**: hello@getspinnable.ai

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Anthropic** for the Model Context Protocol framework
- **Publer** for their comprehensive social media management API
- **The MCP Community** for inspiration and best practices

## 🔗 Related Projects

- [MCP Servers](https://github.com/modelcontextprotocol/servers) - Official MCP servers
- [Claude Desktop](https://claude.ai/download) - AI assistant with MCP support
- [Publer API Documentation](https://app.publer.io/api-docs) - Official API docs

---

**Built with ❤️ by [Spinnable AI](https://getspinnable.ai)**

*Making AI-powered social media management accessible to everyone.*