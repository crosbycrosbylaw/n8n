# n8n Workflow Automation Server

A customized n8n workflow automation server setup with robust serving capabilities, auto-restart functionality, and Python utilities for lightweight server deployment.

## Features

- 🚀 **Robust Server Management**: Auto-restart, health checks, and monitoring
- 🔄 **Multiple Runtime Support**: Works with Bun, Node.js, or npm
- 🐍 **Python Utilities**: HTML parsing and data extraction tools
- ⚡ **Remote Command Execution**: Enhanced PowerShell remote session management
- 🛡️ **Production Ready**: Systemd service integration for lightweight servers
- 📊 **Comprehensive Logging**: Detailed logging and monitoring capabilities

## Quick Start

### Development Mode

```bash
# Start n8n server with monitoring
npm run serve:monitor

# Check server status
npm run serve:status

# View logs
npm run serve:logs

# Stop server
npm run serve:stop
```

### Production Deployment

```bash
# Install as system service (requires sudo)
npm run install:service

# Enable and start service
sudo systemctl enable n8n
sudo systemctl start n8n

# Check service status
sudo systemctl status n8n

# View service logs
sudo journalctl -u n8n -f
```

## Server Management

The `serve-n8n.sh` script provides comprehensive server management:

```bash
./serve-n8n.sh start      # Start server
./serve-n8n.sh stop       # Stop server
./serve-n8n.sh restart    # Restart server
./serve-n8n.sh status     # Check status
./serve-n8n.sh monitor    # Start with auto-restart monitoring
./serve-n8n.sh logs [N]   # Show last N lines of logs (default: 50)
```

### Features:
- **Auto-restart**: Automatically restarts failed processes (configurable limits)
- **Health checks**: Monitors server responsiveness
- **Fallback runtimes**: Tries Bun → npx → npm in order
- **Comprehensive logging**: Separate logs for application and errors
- **Resource monitoring**: Shows CPU and memory usage
- **Graceful shutdown**: Proper cleanup on termination

## Python Utilities

The Python utilities provide HTML parsing and data extraction capabilities:

```bash
# Using pixi (recommended)
pixi run x parser.app parse_link --help
pixi run x parser.app parse_response --help

# Direct execution
cd python
python -m typer parser.app:app run parse_link --help
```

## Remote Command Execution

Enhanced PowerShell remote session management with automatic retry and error handling:

```bash
# Test connection
pixi run invoke "Get-Date; echo 'Connection alive'"

# Execute custom commands
pixi run invoke "Your-PowerShell-Command-Here"
```

### Features:
- **Session management**: Automatic session creation and recovery
- **Retry logic**: Automatic retry on connection failures
- **Error handling**: Comprehensive error reporting and recovery
- **Connection persistence**: Maintains long-lived remote sessions

## Configuration

### Environment Variables

- `N8N_PORT`: Server port (default: 5678)
- `N8N_HOST`: Server host (default: 0.0.0.0 for production)
- `N8N_LOG_LEVEL`: Logging level (default: info)
- `NODE_ENV`: Environment mode (production/development)

### Customization

Edit configuration in:
- `serve-n8n.sh`: Server management settings
- `pixi.toml`: Python dependencies and task configuration
- `package.json`: Node.js dependencies and scripts
- `n8n.service`: Systemd service configuration

## File Structure

```
├── serve-n8n.sh          # Main server management script
├── install-service.sh    # System service installation script  
├── n8n.service          # Systemd service definition
├── package.json         # Node.js configuration
├── pixi.toml           # Python environment and tasks
├── python/             # Python utilities
│   ├── parser/         # HTML parsing tools
│   └── utils/          # Utility functions
└── logs/              # Application logs (created at runtime)
```

## Dependencies

### Node.js Runtime (one of):
- [Bun](https://bun.sh/) (recommended for performance)
- Node.js with npx
- npm

### Python Environment:
- Python 3.11+
- [Pixi](https://pixi.sh/) (recommended) or pip
- BeautifulSoup4, Typer, and other dependencies (see `pixi.toml`)

### System Dependencies:
- curl (for health checks)
- systemd (for service installation)

## Installation

### 1. Clone and Setup

```bash
git clone <repository-url>
cd n8n
```

### 2. Install Node.js Dependencies

```bash
# Using Bun (recommended)
bun install

# Using npm
npm install
```

### 3. Setup Python Environment

```bash
# Using Pixi (recommended)
pixi install

# Using pip
cd python
pip install -e .
```

### 4. Start Development Server

```bash
npm run serve:monitor
```

### 5. Access n8n

Open http://localhost:5678 in your browser.

## Troubleshooting

### Server Won't Start
1. Check if port 5678 is available: `netstat -tlnp | grep 5678`
2. Verify Node.js runtime is installed: `which bun` or `which node`
3. Check logs: `npm run serve:logs`

### Service Issues
1. Check service status: `sudo systemctl status n8n`
2. View service logs: `sudo journalctl -u n8n -f`
3. Verify file permissions: `ls -la /opt/n8n/`

### Python Utilities
1. Verify Python installation: `python --version`
2. Check package installation: `cd python && python -c "import parser"`
3. Test pixi environment: `pixi run x --help`

## Contributing

1. Follow existing code style and conventions
2. Test changes thoroughly with `npm run serve:monitor`
3. Update documentation for new features
4. Ensure backward compatibility

## License

This project follows the same license as the underlying n8n project.