# MDF MCP Server

A Model Context Protocol (MCP) server for analyzing ASAM MDF (Measurement Data Format) files. Enables AI assistants to access and analyze automotive and industrial measurement data.

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Build the Docker image
docker build -t mdfmcp .

# Run the server
docker run -it --rm mdfmcp
```

### Local Development

```bash
# Clone and setup
git clone https://github.com/yourusername/mdfmcp
cd mdfmcp

# Install dependencies
pip install -r requirements.txt

# Run the server
python -m mdfmcp.server
```

## 📋 Features

- **MDF File Support**: Versions 2.x, 3.x, and 4.x
- **AI-Native Interface**: Designed for LLM integration
- **Data Analysis**: Statistics, plotting, signal processing
- **Format Export**: CSV, HDF5, Parquet, MATLAB
- **Session Management**: Multi-file support
- **High Performance**: Efficient large file handling

## 🔧 Configuration

### For Cursor IDE

Add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "mdfmcp": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "mdfmcp"]
    }
  }
}
```

### For Other MCP Clients

```json
{
  "mcpServers": {
    "mdfmcp": {
      "command": "python",
      "args": ["-m", "mdfmcp.server"],
      "env": {
        "PYTHONPATH": "/path/to/mdfmcp/src"
      }
    }
  }
}
```

## 📊 Usage Examples

### Open and Analyze MDF Files

```
User: Open the measurement file at /data/test_drive.mf4
Assistant: I'll open that MDF file for you.

[Opens file]
Successfully opened test_drive.mf4:
- Session ID: mdf_a3b2c1d4
- Version: 4.10
- Channels: 847
- Duration: 1823.4 seconds
```

### List and Search Channels

```
User: What temperature channels are available?
Assistant: Let me search for temperature-related channels.

Found 23 temperature channels:
- Engine_Temp (°C) - Engine coolant temperature
- Oil_Temp (°C) - Engine oil temperature
- Ambient_Temp (°C) - Outside air temperature
```

### Analyze and Plot Signals

```
User: Show me the engine speed statistics and plot it
Assistant: I'll analyze the engine speed signal.

Engine Speed Analysis:
- Mean: 2,847 RPM
- Max: 6,234 RPM
- Std Dev: 1,123 RPM

[Shows time-series plot of engine speed]
```

## 🛠️ Available Tools

### Session Management
- `open_mdf` - Open an MDF file
- `close_mdf` - Close a session
- `list_sessions` - Show active sessions
- `get_file_info` - Get file metadata

### Data Access
- `list_channels` - List available channels
- `mdf_get` - Extract single channel data
- `mdf_select` - Extract multiple channels
- `mdf_get_master` - Get time channel data

### Analysis
- `calculate_statistics` - Compute signal statistics
- `plot_signals` - Create visualizations
- `mdf_to_dataframe` - Convert to pandas DataFrame

### Data Manipulation
- `mdf_cut` - Extract time slice
- `mdf_filter` - Filter specific channels
- `mdf_resample` - Change sampling rate

### Export
- `mdf_export` - Export to various formats
- `mdf_convert` - Convert between MDF versions
- `mdf_save` - Save modified file

## 🐳 Docker Deployment

### Build Image

```bash
docker build -t mdfmcp .
```

### Run Container

```bash
# Basic run
docker run -it --rm mdfmcp

# With volume mount for data
docker run -it --rm -v /path/to/mdf/files:/data mdfmcp

# With custom environment
docker run -it --rm -e MAX_SESSIONS=20 mdfmcp
```

### Docker Compose

```yaml
version: '3.8'
services:
  mdfmcp:
    build: .
    volumes:
      - ./data:/data
    environment:
      - MAX_SESSIONS=10
      - SESSION_TIMEOUT=3600
```

## 🧪 Testing

```bash
# Run tests
pytest tests/

# Test server manually
python tests/manual_test.py
```

## 📁 Project Structure

```
mdfmcp/
├── src/mdfmcp/
│   ├── __init__.py
│   └── server.py          # Main MCP server
├── tests/
│   ├── conftest.py
│   ├── manual_test.py
│   └── test_server.py
├── examples/
│   ├── basic_usage.py
│   └── test_data_generator.py
├── Dockerfile
├── requirements.txt
├── pyproject.toml
└── README.md
```

## 🔧 Development

### Setup Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Code Quality

```bash
# Format code
black src/

# Lint
ruff src/

# Type checking
mypy src/
```

## 🚨 Troubleshooting

### Common Issues

1. **Memory errors with large files**
   - Use `memory="low"` when opening files
   - Reduce concurrent sessions

2. **Cannot find channels**
   - Channel names are case-sensitive
   - Use regex patterns for flexible searching

3. **Docker build fails**
   - Ensure Docker is running
   - Check Dockerfile syntax

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details

## 🙏 Acknowledgments

- Built on [asammdf](https://github.com/danielhrisca/asammdf) by Daniel Hrisca
- Uses the [Model Context Protocol](https://modelcontextprotocol.io) by Anthropic