# SolidWorks MCP Server

A Model Context Protocol (MCP) bridge server for SolidWorks, enabling AI assistants (like Codex) to directly interact with SolidWorks through COM automation.

## Features

- Connect to SolidWorks and control it programmatically
- Open, save, close SolidWorks documents (.sldprt / .sldasm / .slddrw)
- Read document info: features, bodies, mass properties, custom properties
- Export to STEP / IGES / STL formats
- Read file metadata without launching SolidWorks GUI
- Full MCP integration: tools + resources

## Prerequisites

- **SolidWorks** (2020+ recommended) installed on Windows
- **Python 3.10+**
- **pywin32** (`pip install pywin32`)
- **mcp** (`pip install mcp`)

## Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/solidworks-mcp.git
cd solidworks-mcp

# Install dependencies
pip install -r requirements.txt
```

## Usage

### 1. Standalone Mode

Run the MCP server directly:

```bash
python server.py
```

### 2. Codex Integration

Add the following to your Codex `config.toml` (usually at `~/.codex/config.toml`):

```toml
[mcp_servers.solidworks]
command = "python"
args = ["C:/path/to/solidworks-mcp/server.py"]
startup_timeout_sec = 60

[mcp_servers.solidworks.env]
PYTHONIOENCODING = "utf-8"
```

Restart Codex after updating the config.

### 3. Using the Tools

Once connected, you can ask your AI assistant to:

- "Connect to SolidWorks and open `part.sldprt`"
- "List all features in the current document"
- "Export the model as STEP"
- "Get the mass properties"
- "Show me all custom properties"

## Available MCP Tools

| Tool | Description |
|------|-------------|
| `sw_connect` | Connect to SolidWorks (launch if not running) |
| `sw_open_document` | Open a SolidWorks document |
| `sw_get_document_info` | Get full document information |
| `sw_list_features` | List all modeling features |
| `sw_list_bodies` | List all solid bodies |
| `sw_get_mass_properties` | Get mass, volume, center of mass |
| `sw_get_custom_properties` | Read custom properties |
| `sw_export` | Export to STEP / IGES / STL |
| `sw_save` | Save current document |
| `sw_save_as` | Save document to a new path |
| `sw_close_document` | Close a document |
| `sw_rebuild` | Force rebuild the model |
| `sw_read_file_info` | Read file info without launching GUI |
| `sw_quit` | Exit SolidWorks |

## MCP Resources

- `solidworks://status` - Current connection status and active document info
- `solidworks://file/{path}` - Read file metadata without opening SolidWorks

## Architecture

```
solidworks-mcp/
├── server.py          # MCP Server (tools + resources)
├── sw_bridge.py       # SolidWorks COM bridge core
└── requirements.txt   # Python dependencies
```

The bridge communicates with SolidWorks via the Windows COM automation interface (`SldWorks.Application`). The MCP server wraps these operations into standard MCP tools and resources.

## Limitations

- **Windows only** (COM automation is Windows-specific)
- SolidWorks must be installed locally
- Some operations may require SolidWorks to be running with a valid license
- STL export quality settings may vary by SolidWorks version

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
