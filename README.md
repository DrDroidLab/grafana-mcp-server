# Grafana MCP Server

A Model Context Protocol (MCP) server for Grafana that enables AI assistants to interact with Grafana dashboards, panels, and data sources.

## Features

- Connect to Grafana instances via API
- Retrieve dashboard and panel information
- Query data sources and metrics
- Manage Grafana resources through MCP protocol
- Docker support for easy deployment

## Prerequisites

- Python 3.8+
- Grafana instance with API access
- Grafana API key or admin credentials

## Installation

### Using uv (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd grafana-mcp-server

# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate     # On Windows
```

### Using pip

```bash
# Clone the repository
git clone <your-repo-url>
cd grafana-mcp-server

# Install dependencies
pip install -e .
```

## Configuration

1. Copy the example configuration:

```bash
cp grafana-mcp-server/src/grafana_mcp_server/config.yaml.example grafana-mcp-server/src/grafana_mcp_server/config.yaml
```

2. Edit the configuration file with your Grafana settings:

```yaml
grafana:
  url: "http://localhost:3000"
  api_key: "your-api-key-here"
  # or use username/password
  # username: "admin"
  # password: "admin"
```

## Usage

### Running the MCP Server

```bash
# From the project root
python -m grafana_mcp_server.mcp_server

# Or using the stdio server
python -m grafana_mcp_server.stdio_server
```

### Testing Connection

```bash
# Test Grafana connection
python -m grafana_mcp_server.test_grafana_connection
```

### Using Docker

```bash
# Build the Docker image
docker build -t grafana-mcp-server .

# Run the container
docker run -p 3000:3000 grafana-mcp-server
```

Or using docker-compose:

```bash
docker-compose up -d
```

## Development

### Project Structure

```
grafana-mcp-server/
├── src/
│   └── grafana_mcp_server/
│       ├── __init__.py
│       ├── config.yaml
│       ├── mcp_server.py          # Main MCP server implementation
│       ├── stdio_server.py        # STDIO server for MCP
│       ├── test_grafana_connection.py
│       └── processor/
│           ├── __init__.py
│           ├── grafana_processor.py
│           └── processor.py
├── tests/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=grafana_mcp_server
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

## API Reference

### MCP Tools

The server provides the following MCP tools:

- `test_connection`: Test connection to Grafana API
- `list_dashboards`: List all available dashboards
- `get_dashboard`: Get details of a specific dashboard
- `list_panels`: List panels in a dashboard
- `query_data`: Query data from a specific panel or data source

### Configuration Options

| Option             | Description                 | Default                 |
| ------------------ | --------------------------- | ----------------------- |
| `grafana.url`      | Grafana instance URL        | `http://localhost:3000` |
| `grafana.api_key`  | API key for authentication  | None                    |
| `grafana.username` | Username for authentication | None                    |
| `grafana.password` | Password for authentication | None                    |

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support and questions, please open an issue on GitHub or contact the maintainers.
