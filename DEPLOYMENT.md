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

3. **Configure in your IDE**:
   
   **Note**: This MCP server requires file system access to read MDF files. Use it with IDEs that support local file access like VS Code with Continue.dev or Cursor IDE.

   **If you get "command not found" errors**, find your uvx path:
   ```bash
   which uvx  # On macOS/Linux
   where uvx  # On Windows
   ```
   Then use the full path in your IDE configuration (e.g., `/Users/username/.local/bin/uvx`).

### File Organization

**Workspace-Focused File Handling**: The MCP server intelligently searches for MDF files in your project workspace:

```
your-project/
├── your_data.mf4           # ✅ Found automatically
├── data/
│   └── measurements.mf4    # ✅ Found automatically  
├── measurements/
│   └── test_run.mf4        # ✅ Found automatically
├── test_data/
├── examples/
└── samples/
```

**Usage Examples**:
- **Filename only**: `"test_data.mf4"` → searches workspace directories
- **Relative path**: `"./data/measurements.mf4"` → relative to current directory
- **Absolute path**: `"/full/path/to/file.mf4"` → always works
- **Case insensitive**: `"TEST.MF4"` finds `"test.mf4"`

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