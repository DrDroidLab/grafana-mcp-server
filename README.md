# Grafana MCP Server

## Available Tools

The following tools are available via the MCP server:

- **test_connection**: Verify connectivity to your Grafana instance and configuration.
- **grafana_promql_query**: Execute PromQL queries against Grafana's Prometheus datasource. Fetches metrics data using PromQL expressions, optimizes time series responses to reduce token size.
- **grafana_loki_query**: Query Grafana Loki for log data. Fetches logs for a specified duration (e.g., '5m', '1h', '2d'), converts relative time to absolute timestamps.
- **grafana_get_dashboard_config**: Retrieves dashboard configuration details from the database. Queries the connectors_connectormetadatamodelstore table for dashboard metadata.
- **grafana_query_dashboard_panels**: Execute queries for specific dashboard panels. Can query up to 4 panels at once, supports template variables, optimizes metrics data.
- **grafana_fetch_label_values**: Fetch label values for dashboard variables from Prometheus datasource. Retrieves available values for specific labels (e.g., 'instance', 'job'). Supports optional metric filtering.
- **grafana_fetch_dashboard_variables**: Fetch all variables and their values from a Grafana dashboard. Retrieves dashboard template variables and their current values.
- **grafana_fetch_all_dashboards**: Fetch all dashboards from Grafana with basic information like title, UID, folder, tags, etc.
- **grafana_fetch_datasources**: Fetch all datasources from Grafana with their configuration details.
- **grafana_fetch_folders**: Fetch all folders from Grafana with their metadata and permissions.

## 🚀 Usage & Requirements

### 1. Get Your Grafana API Endpoint & API Key

1. Ensure you have a running Grafana instance (self-hosted or cloud).
2. Generate an API key from your Grafana UI:
   - Go to Configuration → API Keys
   - Create a new API key with appropriate permissions (Admin role recommended for full access)
   - Copy the API key (starts with `glsa_`)

---

## 2. Installation & Running Options

### 2A. Install & Run with uv (Recommended for Local Development)

#### 2A.1. Install dependencies with uv

```bash
uv venv .venv
source .venv/bin/activate
uv sync
```

#### 2A.2. Run the server with uv

```bash
uv run grafana-mcp-server/src/grafana_mcp_server/mcp_server.py
```

- You can also use `uv` to run any other entrypoint scripts as needed.
- Make sure your `config.yaml` is in the same directory as `mcp_server.py` or set the required environment variables (see Configuration section).

---

### 2B. Run with Docker Compose (Recommended for Production/Containerized Environments)

1. Edit `grafana-mcp-server/src/grafana_mcp_server/config.yaml` with your Grafana details (host, API key).
2. Start the server:
   ```bash
   docker compose up -d
   ```
   - The server will run in HTTP (SSE) mode on port 8000 by default.
   - You can override configuration with environment variables (see below).

---

## 3. Configuration

The server loads configuration in the following order of precedence:

1. **Environment Variables** (recommended for Docker/CI):
   - `GRAFANA_HOST`: Grafana instance URL (e.g. `https://your-grafana-instance.com`)
   - `GRAFANA_API_KEY`: Grafana API key (required)
   - `GRAFANA_SSL_VERIFY`: `true` or `false` (default: `true`)
   - `MCP_SERVER_PORT`: Port to run the server on (default: `8000`)
   - `MCP_SERVER_DEBUG`: `true` or `false` (default: `true`)
2. **YAML file fallback** (`config.yaml`):
   ```yaml
   grafana:
     host: "https://your-grafana-instance.com"
     api_key: "your-grafana-api-key-here"
     ssl_verify: "true"
   server:
     port: 8000
     debug: true
   ```

---

## 4. Integration with AI Assistants (e.g., Claude Desktop, Cursor)

You can integrate this MCP server with any tool that supports the MCP protocol. Here are the main options:

### 4A. Using Docker (with environment variables)

```json
{
  "mcpServers": {
    "grafana": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-e",
        "GRAFANA_HOST",
        "-e",
        "GRAFANA_API_KEY",
        "-e",
        "GRAFANA_SSL_VERIFY",
        "drdroidlab/grafana-mcp-server",
        "-t",
        "stdio"
      ],
      "env": {
        "GRAFANA_HOST": "https://your-grafana-instance.com",
        "GRAFANA_API_KEY": "your-grafana-api-key-here",
        "GRAFANA_SSL_VERIFY": "true"
      }
    }
  }
}
```

- The `-t stdio` argument is supported for compatibility with Docker MCP clients (forces stdio handshake mode).
- Adjust the volume path or environment variables as needed for your deployment.

### 4C. Connecting to an Already Running MCP Server (HTTP/SSE)

If you have an MCP server already running (e.g., on a remote host, cloud VM, or Kubernetes), you can connect your AI assistant or tool directly to its HTTP endpoint.

```json
{
  "mcpServers": {
    "grafana": {
      "url": "http://your-server-host:8000/mcp"
    }
  }
}
```

- Replace `your-server-host` with the actual host where your MCP server is running.
- **For local setup, use `localhost` as the server host (i.e., `http://localhost:8000/mcp`).**
- **Use `http` for local or unsecured deployments, and `https` for production or secured deployments.**
- Make sure the server is accessible from your client machine (check firewall, security group, etc.).

---

## Health Check

```bash
curl http://localhost:8000/health
```

The server runs on port 8000 by default.

---

## 5. Project Structure

```
grafana-mcp-server/
│   └── src/
│       └── grafana_mcp_server/
│           ├── __init__.py
│           ├── config.yaml              # Configuration file
│           ├── mcp_server.py            # Main MCP server implementation
│           ├── stdio_server.py          # STDIO server for MCP
│           └── processor/
│               ├── __init__.py
│               ├── grafana_processor.py # Grafana API processor
│               └── processor.py         # Base processor interface
├── tests/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

---

## 6. Troubleshooting

### Common Issues

1. **Connection Failed**:

   - Verify your Grafana instance is running and accessible
   - Check your API key has proper permissions
   - Ensure SSL verification settings match your setup

2. **Authentication Errors**:

   - Verify your API key is correct and not expired
   - Check if your Grafana instance requires additional authentication

3. **Query Failures**:
   - Ensure datasource UIDs are correct
   - Verify PromQL/Loki query syntax
   - Check if the datasource is accessible with your API key

### Debug Mode

Enable debug mode to get more detailed logs:

```bash
export MCP_SERVER_DEBUG=true
```

---

## 7. Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 8. License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 9. Support

1. Need help anywhere? Join our [slack community](https://join.slack.com/t/doctor-droid-demo/shared_invite/zt-2h6eap61w-Bmz76OEU6IykmDy673R1qQ) and message on #mcp channel.
2. Want a 1-click MCP Server? Join the same community and let us know.
3. For issues and questions, please open an issue on GitHub or contact the maintainers.
