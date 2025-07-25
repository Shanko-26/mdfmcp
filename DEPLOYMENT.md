# Deployment Guide

## For Developers (Using your MDF MCP Server)

### Quick Start with uvx (Recommended)

1. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Run the server**:
   ```bash
   uvx mcp-server-mdf
   ```

3. **Configure in Claude Desktop**:
   
   Edit your Claude Desktop config file:
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%AppData%\Claude\claude_desktop_config.json`
   
   Add this configuration:
   ```json
   {
     "mcpServers": {
       "mdf": {
         "command": "uvx",
         "args": ["mcp-server-mdf"]
       }
     }
   }
   ```

4. **Restart Claude Desktop** - the MDF tools will appear in the interface

### Advanced Configuration

**With custom arguments**:
```json
{
  "mcpServers": {
    "mdf": {
      "command": "uvx", 
      "args": ["mcp-server-mdf", "--max-sessions", "20", "--session-timeout", "7200"]
    }
  }
}
```

**For VS Code with Continue.dev**:
```json
{
  "mcpServers": {
    "mdf": {
      "command": "uvx",
      "args": ["mcp-server-mdf"]
    }
  }
}
```

## For Package Maintainers

### Publishing to PyPI

1. **Build the package**:
   ```bash
   python -m build
   ```

2. **Upload to PyPI**:
   ```bash
   twine upload dist/*
   ```

3. **Test installation**:
   ```bash
   uvx mcp-server-mdf
   ```

### GitHub Actions Workflow

The repository includes automated PyPI publishing via GitHub Actions:
- Triggers on GitHub releases
- Builds and tests the package
- Publishes to PyPI automatically

Set the `PYPI_API_TOKEN` secret in your repository settings.

### Version Bumping

Update version in `pyproject.toml`:
```toml
version = "0.2.0"
```

## Troubleshooting

### "Command not found" Error
```bash
# Get full path to uv
which uv

# Use full path in config
{
  "mcpServers": {
    "mdf": {
      "command": "/path/to/uv",
      "args": ["run", "mcp-server-mdf"]
    }
  }
}
```

### Communication Issues
- Check Claude Desktop logs: `~/Library/Logs/Claude/mcp.log`
- Verify no stderr output in server code
- Test with: `echo '{"jsonrpc":"2.0","method":"initialize",...}' | uvx mcp-server-mdf`

### Dependencies
All dependencies are automatically managed by uvx. No manual Python environment setup required.