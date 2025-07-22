import datetime
import json
import logging
import os
import sys

import yaml
from flask import Flask, current_app, jsonify, request

from src.grafana_mcp_server.processor.grafana_processor import GrafanaApiProcessor
from src.grafana_mcp_server.stdio_server import run_stdio_server

app = Flask(__name__)
logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Load configuration from environment variables, then YAML as fallback
def load_config():
    # Try multiple possible config file locations
    possible_config_paths = [
        os.path.join(os.path.dirname(__file__), "config.yaml"),  # Same directory as this file
        "/app/config.yaml",  # Docker container path
        "config.yaml",  # Current working directory
    ]
    
    config = {}
    config_loaded = False
    
    for config_path in possible_config_paths:
        try:
            with open(config_path) as file:
                config = yaml.safe_load(file)
                logger.info(f"Successfully loaded config from: {config_path}")
                config_loaded = True
                break
        except FileNotFoundError:
            logger.debug(f"Config file not found at: {config_path}")
            continue
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration from {config_path}: {e}")
            continue
    
    if not config_loaded:
        logger.warning("No config file found, using environment variables only")
        config = {}

    # Environment variable overrides (preferred method)
    grafana_host = os.environ.get("GRAFANA_HOST") or (config.get("grafana", {}).get("host") if config.get("grafana") else None)
    grafana_api_key = os.environ.get("GRAFANA_API_KEY") or (config.get("grafana", {}).get("api_key") if config.get("grafana") else None)
    grafana_ssl_verify = os.environ.get("GRAFANA_SSL_VERIFY") or (
        config.get("grafana", {}).get("ssl_verify", "true") if config.get("grafana") else "true"
    )
    
    server_port = int(os.environ.get("MCP_SERVER_PORT") or (config.get("server", {}).get("port", 8000) if config.get("server") else 8000))
    server_debug = os.environ.get("MCP_SERVER_DEBUG")
    if server_debug is not None:
        server_debug = server_debug.lower() in ["1", "true", "yes"]
    else:
        server_debug = config.get("server", {}).get("debug", True) if config.get("server") else True

    logger.info(f"Loaded configuration - Host: {grafana_host}, API Key: {'***' if grafana_api_key else 'None'}, Port: {server_port}")
    
    return {
        "grafana": {
            "host": grafana_host, 
            "api_key": grafana_api_key,
            "ssl_verify": grafana_ssl_verify
        },
        "server": {"port": server_port, "debug": server_debug},
    }


# Initialize configuration and processor at app startup
with app.app_context():
    config = load_config()
    app.config["GRAFANA_CONFIG"] = config.get("grafana", {})
    app.config["SERVER_CONFIG"] = config.get("server", {})
    
    # Initialize Grafana processor
    try:
        app.config["grafana_processor"] = GrafanaApiProcessor(
            grafana_host=app.config["GRAFANA_CONFIG"].get("host"),
            grafana_api_key=app.config["GRAFANA_CONFIG"].get("api_key"),
            ssl_verify=app.config["GRAFANA_CONFIG"].get("ssl_verify", "true"),
        )
        logger.info("Grafana processor initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Grafana processor: {e}")
        app.config["grafana_processor"] = None

# Server info
SERVER_INFO = {"name": "grafana-mcp-server", "version": "1.0.0"}

# Server capabilities
SERVER_CAPABILITIES = {"tools": {}}

# Protocol version
PROTOCOL_VERSION = "2025-06-18"


def get_current_time_iso():
    """Get current time in ISO format"""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# Available tools - Grafana MCP Server Tools
TOOLS_LIST = [
    {
        "name": "test_connection",
        "description": "Test connection to Grafana API to verify configuration and connectivity. Requires API key or open Grafana instance.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "grafana_promql_query",
        "description": "Executes PromQL queries against Grafana's Prometheus datasource. Fetches metrics data using PromQL expressions, optimizes time series responses to reduce token size.",
        "inputSchema": {
            "type": "object", 
            "properties": {
                "datasource_uid": {"type": "string", "description": "Prometheus datasource UID"},
                "query": {"type": "string", "description": "PromQL query string"},
                "start_time": {
                    "type": "string", 
                    "description": "Start time in RFC3339 or relative string (e.g., 'now-2h', '2023-01-01T00:00:00Z')"
                },
                "end_time": {
                    "type": "string", 
                    "description": "End time in RFC3339 or relative string (e.g., 'now-2h', '2023-01-01T00:00:00Z')"
                },
                "duration": {
                    "type": "string", 
                    "description": "Duration string for the time window (e.g., '2h', '90m')"
                }
            },
            "required": ["datasource_uid", "query"]
        },
    },
    {
        "name": "grafana_loki_query",
        "description": "Queries Grafana Loki for log data. Fetches logs for a specified duration (e.g., '5m', '1h', '2d'), converts relative time to absolute timestamps.",
        "inputSchema": {
            "type": "object", 
            "properties": {
                "query": {"type": "string", "description": "Loki query string"},
                "duration": {"type": "string", "description": "Time duration (e.g., '5m', '1h', '2d') - overrides start_time/end_time if provided"},
                "start_time": {
                    "type": "string", 
                    "description": "Start time in RFC3339 or relative string (e.g., 'now-2h', '2023-01-01T00:00:00Z')"
                },
                "end_time": {
                    "type": "string", 
                    "description": "End time in RFC3339 or relative string (e.g., 'now-2h', '2023-01-01T00:00:00Z')"
                },
                "limit": {"type": "integer", "description": "Maximum number of log entries to return", "default": 100}
            },
            "required": ["query"]
        },
    },
    {
        "name": "grafana_get_dashboard_config",
        "description": "Retrieves dashboard configuration details from the database. Queries the connectors_connectormetadatamodelstore table for dashboard metadata.",
        "inputSchema": {
            "type": "object", 
            "properties": {
                "dashboard_uid": {"type": "string", "description": "Dashboard UID"}
            },
            "required": ["dashboard_uid"]
        },
    },
    {
        "name": "grafana_query_dashboard_panels",
        "description": "Executes queries for specific dashboard panels. Can query up to 4 panels at once, supports template variables, optimizes metrics data.",
        "inputSchema": {
            "type": "object", 
            "properties": {
                "dashboard_uid": {"type": "string", "description": "Dashboard UID"},
                "panel_ids": {"type": "array", "items": {"type": "integer"}, "description": "List of panel IDs to query (max 4)"},
                "template_variables": {"type": "object", "description": "Template variables for the dashboard"}
            },
            "required": ["dashboard_uid", "panel_ids"]
        },
    },
    {
        "name": "grafana_fetch_label_values",
        "description": "Fetches label values for dashboard variables from Prometheus datasource. Retrieves available values for specific labels (e.g., 'instance', 'job').",
        "inputSchema": {
            "type": "object", 
            "properties": {
                "datasource_uid": {"type": "string", "description": "Prometheus datasource UID"},
                "label_name": {"type": "string", "description": "Label name to fetch values for (e.g., 'instance', 'job')"}
            },
            "required": ["datasource_uid", "label_name"]
        },
    },
    {
        "name": "grafana_fetch_dashboard_variables",
        "description": "Fetches all variables and their values from a Grafana dashboard. Retrieves dashboard template variables and their current values.",
        "inputSchema": {
            "type": "object", 
            "properties": {
                "dashboard_uid": {"type": "string", "description": "Dashboard UID"}
            },
            "required": ["dashboard_uid"]
        },
    },
    {
        "name": "grafana_fetch_all_dashboards",
        "description": "Fetches all dashboards from Grafana with basic information like title, UID, folder, tags, etc.",
        "inputSchema": {
            "type": "object", 
            "properties": {
                "limit": {"type": "integer", "description": "Maximum number of dashboards to return", "default": 100}
            },
            "required": []
        },
    },
    {
        "name": "grafana_fetch_datasources",
        "description": "Fetches all datasources from Grafana with their configuration details.",
        "inputSchema": {
            "type": "object", 
            "properties": {},
            "required": []
        },
    },
    {
        "name": "grafana_fetch_folders",
        "description": "Fetches all folders from Grafana with their metadata and permissions.",
        "inputSchema": {
            "type": "object", 
            "properties": {},
            "required": []
        },
    }
]


# Tool implementations
def test_grafana_connection():
    """Test connection to Grafana API"""
    try:
        grafana_processor = current_app.config.get("grafana_processor")
        if not grafana_processor:
            return {"status": "error", "message": "Grafana processor not initialized. Check configuration."}
        
        result = grafana_processor.test_connection()
        
        if result:
            connection_details = grafana_processor.get_connection()
            return {
                "status": "success", 
                "message": "Successfully connected to Grafana API",
                "auth_method": connection_details.get("auth_method"),
                "host": connection_details.get("host")
            }
        else:
            return {"status": "failed", "message": "Failed to connect to Grafana API"}
    except Exception as e:
        logger.error(f"Error testing Grafana connection: {str(e)}")
        return {"status": "error", "message": f"Failed to connect to Grafana: {str(e)}"}


def grafana_promql_query(datasource_uid, query, start_time=None, end_time=None, duration=None):
    """Execute PromQL query against Grafana's Prometheus datasource"""
    try:
        grafana_processor = current_app.config.get("grafana_processor")
        if not grafana_processor:
            return {"status": "error", "message": "Grafana processor not initialized. Check configuration."}
        
        result = grafana_processor.grafana_promql_query(datasource_uid, query, start_time, end_time, duration)
        return result
    except Exception as e:
        logger.error(f"Error executing PromQL query: {str(e)}")
        return {"status": "error", "message": f"PromQL query failed: {str(e)}"}


def grafana_loki_query(query, duration=None, start_time=None, end_time=None, limit=100):
    """Query Grafana Loki for log data"""
    try:
        grafana_processor = current_app.config.get("grafana_processor")
        if not grafana_processor:
            return {"status": "error", "message": "Grafana processor not initialized. Check configuration."}
        
        result = grafana_processor.grafana_loki_query(query, duration, start_time, end_time, limit)
        return result
    except Exception as e:
        logger.error(f"Error executing Loki query: {str(e)}")
        return {"status": "error", "message": f"Loki query failed: {str(e)}"}


def grafana_get_dashboard_config(dashboard_uid):
    """Get dashboard configuration details"""
    try:
        grafana_processor = current_app.config.get("grafana_processor")
        if not grafana_processor:
            return {"status": "error", "message": "Grafana processor not initialized. Check configuration."}
        
        result = grafana_processor.grafana_get_dashboard_config_details(dashboard_uid)
        return result
    except Exception as e:
        logger.error(f"Error fetching dashboard config: {str(e)}")
        return {"status": "error", "message": f"Failed to fetch dashboard config: {str(e)}"}


def grafana_query_dashboard_panels(dashboard_uid, panel_ids, template_variables=None):
    """Execute queries for specific dashboard panels"""
    try:
        grafana_processor = current_app.config.get("grafana_processor")
        if not grafana_processor:
            return {"status": "error", "message": "Grafana processor not initialized. Check configuration."}
        
        result = grafana_processor.grafana_query_dashboard_panels(dashboard_uid, panel_ids, template_variables)
        return result
    except Exception as e:
        logger.error(f"Error querying dashboard panels: {str(e)}")
        return {"status": "error", "message": f"Failed to query dashboard panels: {str(e)}"}


def grafana_fetch_label_values(datasource_uid, label_name):
    """Fetch label values for dashboard variables from Prometheus datasource"""
    try:
        grafana_processor = current_app.config.get("grafana_processor")
        if not grafana_processor:
            return {"status": "error", "message": "Grafana processor not initialized. Check configuration."}
        
        result = grafana_processor.grafana_fetch_dashboard_variable_label_values(datasource_uid, label_name)
        return result
    except Exception as e:
        logger.error(f"Error fetching label values: {str(e)}")
        return {"status": "error", "message": f"Failed to fetch label values: {str(e)}"}


def grafana_fetch_dashboard_variables(dashboard_uid):
    """Fetch all variables and their values from a Grafana dashboard"""
    try:
        grafana_processor = current_app.config.get("grafana_processor")
        if not grafana_processor:
            return {"status": "error", "message": "Grafana processor not initialized. Check configuration."}
        
        result = grafana_processor.grafana_fetch_dashboard_variables(dashboard_uid)
        return result
    except Exception as e:
        logger.error(f"Error fetching dashboard variables: {str(e)}")
        return {"status": "error", "message": f"Failed to fetch dashboard variables: {str(e)}"}


def grafana_fetch_all_dashboards(limit=100):
    """Fetch all dashboards from Grafana"""
    try:
        grafana_processor = current_app.config.get("grafana_processor")
        if not grafana_processor:
            return {"status": "error", "message": "Grafana processor not initialized. Check configuration."}
        
        result = grafana_processor.grafana_fetch_all_dashboards(limit)
        return result
    except Exception as e:
        logger.error(f"Error fetching dashboards: {str(e)}")
        return {"status": "error", "message": f"Failed to fetch dashboards: {str(e)}"}


def grafana_fetch_datasources():
    """Fetch all datasources from Grafana"""
    try:
        grafana_processor = current_app.config.get("grafana_processor")
        if not grafana_processor:
            return {"status": "error", "message": "Grafana processor not initialized. Check configuration."}
        
        result = grafana_processor.grafana_fetch_datasources()
        return result
    except Exception as e:
        logger.error(f"Error fetching datasources: {str(e)}")
        return {"status": "error", "message": f"Failed to fetch datasources: {str(e)}"}


def grafana_fetch_folders():
    """Fetch all folders from Grafana"""
    try:
        grafana_processor = current_app.config.get("grafana_processor")
        if not grafana_processor:
            return {"status": "error", "message": "Grafana processor not initialized. Check configuration."}
        
        result = grafana_processor.grafana_fetch_folders()
        return result
    except Exception as e:
        logger.error(f"Error fetching folders: {str(e)}")
        return {"status": "error", "message": f"Failed to fetch folders: {str(e)}"}


# Function mapping
FUNCTION_MAPPING = {
    "test_connection": test_grafana_connection,
    "grafana_promql_query": grafana_promql_query,
    "grafana_loki_query": grafana_loki_query,
    "grafana_get_dashboard_config": grafana_get_dashboard_config,
    "grafana_query_dashboard_panels": grafana_query_dashboard_panels,
    "grafana_fetch_label_values": grafana_fetch_label_values,
    "grafana_fetch_dashboard_variables": grafana_fetch_dashboard_variables,
    "grafana_fetch_all_dashboards": grafana_fetch_all_dashboards,
    "grafana_fetch_datasources": grafana_fetch_datasources,
    "grafana_fetch_folders": grafana_fetch_folders,
}


def handle_jsonrpc_request(data):
    """Handle JSON-RPC 2.0 requests"""
    request_id = data.get("id")
    method = data.get("method")
    params = data.get("params", {})

    logger.info(f"Handling JSON-RPC request: {method}")

    # Handle JSON-RPC notifications (no id field or method starts with 'notifications/')
    if method and method.startswith("notifications/"):
        logger.info(f"Received notification: {method}")
        return {"jsonrpc": "2.0", "result": {}, "id": request_id}

    # Handle initialization
    if method == "initialize":
        client_protocol_version = params.get("protocolVersion")
        # Accept any protocol version that starts with '2025-'
        if not (isinstance(client_protocol_version, str) and client_protocol_version.startswith("2025-")):
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32602, "message": f"Unsupported protocol version: {client_protocol_version}"},
                "id": request_id,
            }
        
        return {
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": SERVER_CAPABILITIES,
                "serverInfo": SERVER_INFO,
            },
            "id": request_id,
        }

    # Handle tools/list
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "result": {"tools": TOOLS_LIST},
            "id": request_id,
        }

    # Handle tools/call
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in FUNCTION_MAPPING:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
                "id": request_id,
            }
        
        try:
            # Execute the tool function
            result = FUNCTION_MAPPING[tool_name](**arguments)
            
            return {
                "jsonrpc": "2.0",
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
                    "isError": False,
                },
                "id": request_id,
            }
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"Tool execution failed: {str(e)}"},
                "id": request_id,
            }

    # Unknown method
    else:
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32601, "message": f"Method not found: {method}"},
            "id": request_id,
        }


@app.route("/mcp", methods=["POST"])
def mcp_endpoint():
    """Main MCP endpoint for JSON-RPC requests"""
    if request.method != "POST":
        return jsonify({"error": "Only POST method is supported. Use POST with application/json."}), 405

    data = request.get_json()
    logger.info(f"Received MCP request: {data}")

    if not data:
        return jsonify({"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None}), 400

    response = handle_jsonrpc_request(data)
    status_code = 200
    
    if "error" in response:
        # Map error codes to HTTP status codes
        code = response["error"].get("code", -32000)
        if code == -32700 or code == -32600 or code == -32602:
            status_code = 400
        elif code == -32601:
            status_code = 404
        else:
            status_code = 500
            
    return jsonify(response), status_code


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok", "timestamp": get_current_time_iso()})


@app.route("/", methods=["GET"])
def root():
    """Root endpoint with server info"""
    return jsonify({
        "name": "Grafana MCP Server",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "mcp": "/mcp",
            "health": "/health"
        }
    })


def main():
    """Main entry point"""
    transport = os.environ.get("MCP_TRANSPORT", "http")
    
    if ("-t" in sys.argv and "stdio" in sys.argv) or ("--transport" in sys.argv and "stdio" in sys.argv) or (transport == "stdio"):
        def stdio_handler(data):
            with app.app_context():
                return handle_jsonrpc_request(data)

        run_stdio_server(stdio_handler)
    else:
        # HTTP mode
        port = app.config["SERVER_CONFIG"].get("port", 8000)
        debug = app.config["SERVER_CONFIG"].get("debug", True)
        logger.info(f"Starting Grafana MCP Server on port {port}")
        app.run(host="0.0.0.0", port=port, debug=debug)


if __name__ == "__main__":
    main()