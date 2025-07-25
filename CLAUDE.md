# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an MCP (Model Context Protocol) server for analyzing ASAM MDF (Measurement Data Format) files. It enables AI assistants to access and analyze automotive and industrial measurement data through a standardized interface.

## Key Architecture

The main implementation is in `src/mdfmcp/server.py:61` - the `MdfMcpServer` class that provides:

- **Session Management**: Multi-file support with timeout handling (`MdfSession` dataclass at `src/mdfmcp/server.py:37`)
- **Dynamic Tool Generation**: Automatically exposes MDF methods as MCP tools (see `EXPOSE_METHODS` at `src/mdfmcp/server.py:65`)
- **Special Handlers**: Custom processing for complex return types (defined in `SPECIAL_HANDLERS` at `src/mdfmcp/server.py:73`)
- **Data Analysis**: Statistics, plotting, and export capabilities

The server exposes 20+ tools dynamically based on the asammdf library API, with special handling for methods that return complex objects like Signal or MDF instances.

## Development Commands

### Local Development
```bash
# Install dependencies 
pip install -r requirements.txt
pip install -e .

# Run server locally  
mcp-server-mdf

# Alternative with PYTHONPATH for development
PYTHONPATH=src python -m mdfmcp.server

# Using Makefile
make run
```

### Testing
```bash
# Run all tests
pytest tests/
make test

# Manual server testing
python tests/manual_test.py
```

### Code Quality
```bash
# Format code
black src/ tests/
make format

# Lint code  
ruff src/ tests/
make lint

# Type checking
mypy src/
make type-check

# Run all checks
make check-all
```

### Docker Development
```bash
# Build image
docker build -t mdfmcp .
make docker-build

# Run container
docker run -it --rm mdfmcp
make docker-run

# Test in container
make docker-test

# Using docker-compose
make docker-compose-up
make docker-compose-logs
make docker-compose-down
```

## Project Structure

- `src/mdfmcp/server.py` - Main MCP server implementation (915 lines)
- `tests/conftest.py` - Test fixtures with realistic automotive signal generation
- `tests/test_server.py` - Server unit tests
- `examples/` - Usage examples and test data generation
- `pyproject.toml` - Python packaging and dependencies
- `Makefile` - Development commands
- `docker-compose.yml` - Container orchestration

## Key Dependencies

- `mcp[cli]>=1.4.0` - Model Context Protocol framework
- `asammdf>=8.0.0` - ASAM MDF file handling
- `numpy>=1.24.0`, `pandas>=2.0.0` - Data processing
- `matplotlib>=3.6.0` - Visualization (configured for headless operation)

## MCP Integration

Configure in MCP clients with uvx (recommended):
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

Alternative Docker configuration:
```json
{
  "mcpServers": {
    "mdf": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "mcp-server-mdf"]
    }
  }
}
```

## Testing Strategy

Tests use realistic automotive signal generation (vehicle speed, engine RPM, coolant temperature) with proper noise and correlations. The `conftest.py` creates temporary MDF files with automotive-grade test data.