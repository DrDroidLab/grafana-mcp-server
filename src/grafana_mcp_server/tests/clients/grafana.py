import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GrafanaMCPClient:
    """
    Client for interacting with the Grafana MCP server for testing purposes.
    Wraps the Flask test client and provides MCP protocol methods.
    """

    def __init__(self, test_client: Any, api_key: str = "test-key"):
        """
        Initialize the Grafana MCP client.
        
        Args:
            test_client: Flask test client instance
            api_key: API key for MCP server (for testing)
        """
        self.test_client = test_client
        self.api_key = api_key
        self.session_initialized = False
        self._initialize_session()

    def _initialize_session(self):
        """Initialize the MCP session."""
        try:
            response = self.test_client.post(
                "/mcp",
                data=json.dumps({
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "test-client", "version": "1.0.0"}
                    },
                    "id": "init-1"
                }),
                content_type="application/json"
            )
            
            if response.status_code == 200:
                self.session_initialized = True
                logger.info("MCP session initialized successfully")
            else:
                logger.error(f"Failed to initialize MCP session: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error initializing MCP session: {e}")

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all available tools from the MCP server.
        
        Returns:
            List of tool definitions
        """
        try:
            response = self.test_client.post(
                "/mcp",
                data=json.dumps({
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "params": {},
                    "id": "tools-list"
                }),
                content_type="application/json"
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to list tools: HTTP {response.status_code}")
                return []
            
            response_data = response.get_json()
            
            if "error" in response_data:
                logger.error(f"MCP error listing tools: {response_data['error']}")
                return []
            
            if "result" in response_data and "tools" in response_data["result"]:
                return response_data["result"]["tools"]
            
            return []
            
        except Exception as e:
            logger.error(f"Exception listing tools: {e}")
            return []

    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool on the MCP server.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters to pass to the tool
            
        Returns:
            Tool execution result
        """
        try:
            response = self.test_client.post(
                "/mcp",
                data=json.dumps({
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": parameters
                    },
                    "id": f"tool-{tool_name}"
                }),
                content_type="application/json"
            )
            
            if response.status_code != 200:
                return {"error": f"HTTP {response.status_code}"}
            
            response_data = response.get_json()
            
            if "error" in response_data:
                return {"error": response_data["error"].get("message", "Unknown MCP error")}
            
            if "result" in response_data:
                result = response_data["result"]
                
                # Extract content from MCP result format
                if "content" in result and isinstance(result["content"], list):
                    if len(result["content"]) > 0:
                        content_item = result["content"][0]
                        if "text" in content_item:
                            try:
                                # Try to parse JSON content
                                return json.loads(content_item["text"])
                            except json.JSONDecodeError:
                                # Return as plain text if not JSON
                                return {"content": content_item["text"]}
                
                # Return raw result if content format is unexpected
                return result
            
            return {"error": "No result in response"}
            
        except Exception as e:
            logger.error(f"Exception executing tool {tool_name}: {e}")
            return {"error": str(e)}

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Grafana via MCP server."""
        return self.execute_tool("test_connection", {})

    def fetch_dashboards(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Fetch dashboards via MCP server."""
        params = {}
        if limit is not None:
            params["limit"] = limit
        return self.execute_tool("grafana_fetch_all_dashboards", params)

    def get_dashboard_config(self, dashboard_uid: str) -> Dict[str, Any]:
        """Get dashboard configuration via MCP server."""
        return self.execute_tool("grafana_get_dashboard_config", {"dashboard_uid": dashboard_uid})

    def promql_query(self, query: str, start_time: str, end_time: str, step: str = "60s", 
                     datasource_uid: Optional[str] = None) -> Dict[str, Any]:
        """Execute PromQL query via MCP server."""
        params = {
            "query": query,
            "start_time": start_time,
            "end_time": end_time,
            "step": step
        }
        if datasource_uid:
            params["datasource_uid"] = datasource_uid
        return self.execute_tool("grafana_promql_query", params)

    def loki_query(self, query: str, start_time: str, end_time: str, limit: int = 100,
                   datasource_uid: Optional[str] = None) -> Dict[str, Any]:
        """Execute Loki query via MCP server."""
        params = {
            "query": query,
            "start_time": start_time,
            "end_time": end_time,
            "limit": limit
        }
        if datasource_uid:
            params["datasource_uid"] = datasource_uid
        return self.execute_tool("grafana_loki_query", params)

    def query_dashboard_panels(self, dashboard_uid: str, start_time: str, end_time: str,
                              variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Query dashboard panels via MCP server."""
        params = {
            "dashboard_uid": dashboard_uid,
            "start_time": start_time,
            "end_time": end_time
        }
        if variables:
            params["variables"] = variables
        return self.execute_tool("grafana_query_dashboard_panels", params)

    def fetch_datasources(self) -> Dict[str, Any]:
        """Fetch datasources via MCP server."""
        return self.execute_tool("grafana_fetch_datasources", {})

    def fetch_folders(self) -> Dict[str, Any]:
        """Fetch folders via MCP server."""
        return self.execute_tool("grafana_fetch_folders", {})

    def fetch_label_values(self, label: str, datasource_uid: Optional[str] = None) -> Dict[str, Any]:
        """Fetch label values via MCP server."""
        params = {"label": label}
        if datasource_uid:
            params["datasource_uid"] = datasource_uid
        return self.execute_tool("grafana_fetch_label_values", params)

    def fetch_dashboard_variables(self, dashboard_uid: str) -> Dict[str, Any]:
        """Fetch dashboard variables via MCP server."""
        return self.execute_tool("grafana_fetch_dashboard_variables", {"dashboard_uid": dashboard_uid})

    def close_session(self):
        """Close the MCP session."""
        self.session_initialized = False
        logger.info("MCP session closed")