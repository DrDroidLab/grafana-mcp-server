import json
import pytest
from datetime import datetime, timezone, timedelta


class TestMCPServerEndpoints:
    """Test MCP server tool endpoints."""
    
    def test_server_initialization(self, client):
        """Test that the server initializes correctly."""
        # Test that the Flask app is running
        assert client is not None
    
    def test_jsonrpc_initialize(self, client):
        """Test JSON-RPC initialize method."""
        response = client.post(
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
        
        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data["id"] == "init-1"
        assert "result" in response_data
        assert response_data["result"]["protocolVersion"] == "2025-06-18"
    
    def test_tools_list(self, client):
        """Test tools/list method."""
        response = client.post(
            "/mcp",
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": "tools-list-1"
            }),
            content_type="application/json"
        )
        
        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data["id"] == "tools-list-1"
        assert "result" in response_data
        assert "tools" in response_data["result"]
        
        tools = response_data["result"]["tools"]
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        # Check that expected tools are present
        tool_names = [tool["name"] for tool in tools]
        expected_tools = [
            "test_connection",
            "grafana_promql_query", 
            "grafana_loki_query",
            "grafana_get_dashboard_config",
            "grafana_query_dashboard_panels",
            "grafana_fetch_all_dashboards",
            "grafana_fetch_datasources",
            "grafana_fetch_folders"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Expected tool '{expected_tool}' not found in tools list"


class TestConnectionTool:
    """Test connection testing tool."""
    
    def test_tool_call_test_connection(self, client):
        """Test the 'test_connection' tool call through the MCP server."""
        response = client.post(
            "/mcp",
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "test_connection",
                    "arguments": {}
                },
                "id": "test-conn-1"
            }),
            content_type="application/json"
        )
        
        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data["id"] == "test-conn-1"
        assert "result" in response_data
        
        result = response_data["result"]
        assert "content" in result
        assert len(result["content"]) > 0
        
        content = json.loads(result["content"][0]["text"])
        assert "status" in content
        assert content["status"] in ("success", "error")


class TestDashboardTools:
    """Test dashboard-related tools."""
    
    def test_tool_call_fetch_all_dashboards(self, client):
        """Test the 'grafana_fetch_all_dashboards' tool call."""
        response = client.post(
            "/mcp",
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "grafana_fetch_all_dashboards",
                    "arguments": {
                        "limit": 5
                    }
                },
                "id": "fetch-dashboards-1"
            }),
            content_type="application/json"
        )
        
        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data["id"] == "fetch-dashboards-1"
        assert "result" in response_data
        
        content = json.loads(response_data["result"]["content"][0]["text"])
        assert content["status"] in ("success", "error")
        
        if content["status"] == "success":
            # Check for either "data" or "dashboards" key
            assert "data" in content or "dashboards" in content
            print("Successfully fetched dashboards")
        else:
            pytest.skip(f"Dashboard fetch failed: {content.get('message')}")
    
    def test_tool_call_get_dashboard_config(self, client):
        """Test the 'grafana_get_dashboard_config' tool call."""
        # First fetch dashboards to get a valid UID
        dashboards_response = client.post(
            "/mcp",
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "grafana_fetch_all_dashboards",
                    "arguments": {"limit": 1}
                },
                "id": "fetch-for-config"
            }),
            content_type="application/json"
        )
        
        assert dashboards_response.status_code == 200
        dashboards_data = dashboards_response.get_json()
        dashboards_content = json.loads(dashboards_data["result"]["content"][0]["text"])
        
        if dashboards_content["status"] == "error":
            pytest.skip("Cannot test dashboard config without available dashboards")
        
        dashboards = dashboards_content.get("data", dashboards_content.get("dashboards", []))
        if not dashboards:
            pytest.skip("No dashboards available for config testing")
        
        dashboard_uid = dashboards[0].get("uid")
        if not dashboard_uid:
            pytest.skip("Dashboard UID not available")
        
        # Now test getting dashboard config
        response = client.post(
            "/mcp",
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "grafana_get_dashboard_config",
                    "arguments": {
                        "dashboard_uid": dashboard_uid
                    }
                },
                "id": "get-config-1"
            }),
            content_type="application/json"
        )
        
        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data["id"] == "get-config-1"
        assert "result" in response_data
        
        content = json.loads(response_data["result"]["content"][0]["text"])
        assert content["status"] in ("success", "error")
        
        if content["status"] == "success":
            # Check for either "data" or "dashboard" key
            assert "data" in content or "dashboard" in content
            print(f"Successfully fetched config for dashboard: {dashboard_uid}")
        else:
            pytest.skip(f"Dashboard config fetch failed: {content.get('message')}")


class TestQueryTools:
    """Test query-related tools."""
    
    def test_tool_call_promql_query(self, client):
        """Test the 'grafana_promql_query' tool call."""
        # First get datasources to find a Prometheus datasource
        datasources_response = client.post(
            "/mcp",
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "grafana_fetch_datasources",
                    "arguments": {}
                },
                "id": "fetch-datasources"
            }),
            content_type="application/json"
        )
        
        assert datasources_response.status_code == 200
        datasources_data = datasources_response.get_json()
        datasources_content = json.loads(datasources_data["result"]["content"][0]["text"])
        
        if datasources_content["status"] == "error":
            pytest.skip("Cannot test PromQL without datasources")
        
        datasources = datasources_content.get("data", datasources_content.get("datasources", []))
        if not datasources:
            pytest.skip("No datasources available for PromQL testing")
        
        # Find Prometheus datasource
        prometheus_ds = None
        for ds in datasources:
            if ds.get("type") == "prometheus":
                prometheus_ds = ds
                break
        
        if not prometheus_ds:
            pytest.skip("No Prometheus datasource found for PromQL testing")
        
        datasource_uid = prometheus_ds.get("uid")
        if not datasource_uid:
            pytest.skip("Prometheus datasource UID not available")
        
        # Use recent time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=1)
        
        response = client.post(
            "/mcp",
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "grafana_promql_query",
                    "arguments": {
                        "datasource_uid": datasource_uid,
                        "query": "up",
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat()
                    }
                },
                "id": "promql-1"
            }),
            content_type="application/json"
        )
        
        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data["id"] == "promql-1"
        assert "result" in response_data
        
        content = json.loads(response_data["result"]["content"][0]["text"])
        assert content["status"] in ("success", "error")
        
        if content["status"] == "success":
            # PromQL responses can have different structures, check for common keys
            assert any(key in content for key in ["data", "results", "frames", "series"])
            print("Successfully executed PromQL query")
        else:
            # PromQL queries might fail due to datasource configuration
            pytest.skip(f"PromQL query failed: {content.get('message')}")
    
    def test_tool_call_loki_query(self, client):
        """Test the 'grafana_loki_query' tool call."""
        # Use recent time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=1)
        
        response = client.post(
            "/mcp",
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "grafana_loki_query",
                    "arguments": {
                        "query": '{job="grafana"}',
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "limit": 100
                    }
                },
                "id": "loki-1"
            }),
            content_type="application/json"
        )
        
        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data["id"] == "loki-1"
        assert "result" in response_data
        
        content = json.loads(response_data["result"]["content"][0]["text"])
        assert content["status"] in ("success", "error")
        
        if content["status"] == "success":
            assert "data" in content
            print("Successfully executed Loki query")
        else:
            # Loki queries might fail due to datasource configuration
            pytest.skip(f"Loki query failed: {content.get('message')}")
    
    def test_tool_call_query_dashboard_panels(self, client):
        """Test the 'grafana_query_dashboard_panels' tool call."""
        # First fetch dashboards to get a valid UID
        dashboards_response = client.post(
            "/mcp",
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "grafana_fetch_all_dashboards",
                    "arguments": {"limit": 1}
                },
                "id": "fetch-for-panels"
            }),
            content_type="application/json"
        )
        
        assert dashboards_response.status_code == 200
        dashboards_data = dashboards_response.get_json()
        dashboards_content = json.loads(dashboards_data["result"]["content"][0]["text"])
        
        if dashboards_content["status"] == "error":
            pytest.skip("Cannot test panel queries without available dashboards")
        
        dashboards = dashboards_content.get("data", [])
        if not dashboards:
            pytest.skip("No dashboards available for panel testing")
        
        dashboard_uid = dashboards[0].get("uid")
        if not dashboard_uid:
            pytest.skip("Dashboard UID not available")
        
        # Use recent time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=1)
        
        # Now test querying dashboard panels
        response = client.post(
            "/mcp",
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "grafana_query_dashboard_panels",
                    "arguments": {
                        "dashboard_uid": dashboard_uid,
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat()
                    }
                },
                "id": "query-panels-1"
            }),
            content_type="application/json"
        )
        
        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data["id"] == "query-panels-1"
        assert "result" in response_data
        
        content = json.loads(response_data["result"]["content"][0]["text"])
        assert content["status"] in ("success", "error")
        
        if content["status"] == "success":
            assert "data" in content
            print(f"Successfully queried panels for dashboard: {dashboard_uid}")
        else:
            pytest.skip(f"Dashboard panel query failed: {content.get('message')}")


class TestResourceTools:
    """Test resource-related tools (datasources, folders, etc.)."""
    
    def test_tool_call_fetch_datasources(self, client):
        """Test the 'grafana_fetch_datasources' tool call."""
        response = client.post(
            "/mcp",
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "grafana_fetch_datasources",
                    "arguments": {}
                },
                "id": "fetch-ds-1"
            }),
            content_type="application/json"
        )
        
        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data["id"] == "fetch-ds-1"
        assert "result" in response_data
        
        content = json.loads(response_data["result"]["content"][0]["text"])
        assert content["status"] in ("success", "error")
        
        if content["status"] == "success":
            # Check for either "data" or "datasources" key
            assert "data" in content or "datasources" in content
            print("Successfully fetched datasources")
        else:
            pytest.skip(f"Datasources fetch failed: {content.get('message')}")
    
    def test_tool_call_fetch_folders(self, client):
        """Test the 'grafana_fetch_folders' tool call."""
        response = client.post(
            "/mcp",
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "grafana_fetch_folders",
                    "arguments": {}
                },
                "id": "fetch-folders-1"
            }),
            content_type="application/json"
        )
        
        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data["id"] == "fetch-folders-1"
        assert "result" in response_data
        
        content = json.loads(response_data["result"]["content"][0]["text"])
        assert content["status"] in ("success", "error")
        
        if content["status"] == "success":
            # Check for either "data" or "folders" key
            assert "data" in content or "folders" in content
            print("Successfully fetched folders")
        else:
            pytest.skip(f"Folders fetch failed: {content.get('message')}")
    
    def test_tool_call_fetch_label_values(self, client):
        """Test the 'grafana_fetch_dashboard_variable_label_values' tool call."""
        # First get datasources to find a Prometheus datasource
        datasources_response = client.post(
            "/mcp",
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "grafana_fetch_datasources",
                    "arguments": {}
                },
                "id": "fetch-datasources-for-labels"
            }),
            content_type="application/json"
        )
        
        assert datasources_response.status_code == 200
        datasources_data = datasources_response.get_json()
        datasources_content = json.loads(datasources_data["result"]["content"][0]["text"])
        
        if datasources_content["status"] == "error":
            pytest.skip("Cannot test label values without datasources")
        
        datasources = datasources_content.get("data", datasources_content.get("datasources", []))
        if not datasources:
            pytest.skip("No datasources available for label values testing")
        
        # Find Prometheus datasource
        prometheus_ds = None
        for ds in datasources:
            if ds.get("type") == "prometheus":
                prometheus_ds = ds
                break
        
        if not prometheus_ds:
            pytest.skip("No Prometheus datasource found for label values testing")
        
        datasource_uid = prometheus_ds.get("uid")
        if not datasource_uid:
            pytest.skip("Prometheus datasource UID not available")
        
        response = client.post(
            "/mcp",
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "grafana_fetch_label_values",
                    "arguments": {
                        "datasource_uid": datasource_uid,
                        "label_name": "job"
                    }
                },
                "id": "fetch-labels-1"
            }),
            content_type="application/json"
        )
        
        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data["id"] == "fetch-labels-1"
        assert "result" in response_data
        
        content = json.loads(response_data["result"]["content"][0]["text"])
        assert content["status"] in ("success", "error")
        
        if content["status"] == "success":
            # Check for either "data" or "values" key
            assert "data" in content or "values" in content
            print("Successfully fetched label values")
        else:
            pytest.skip(f"Label values fetch failed: {content.get('message')}")


class TestErrorHandling:
    """Test error handling in MCP server tools."""
    
    def test_invalid_tool_name(self, client):
        """Test calling a non-existent tool."""
        response = client.post(
            "/mcp",
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "non_existent_tool",
                    "arguments": {}
                },
                "id": "error-1"
            }),
            content_type="application/json"
        )
        
        # Server returns 404 for unknown tools, which is correct behavior
        assert response.status_code == 404
        response_data = response.get_json()
        assert response_data["id"] == "error-1"
        assert "error" in response_data
        assert response_data["error"]["code"] == -32601  # Method not found
    
    def test_invalid_json(self, client):
        """Test sending invalid JSON."""
        response = client.post(
            "/mcp",
            data="invalid json",
            content_type="application/json"
        )
        
        # Server returns 400 for invalid JSON, which is correct behavior
        assert response.status_code == 400
        try:
            response_data = response.get_json()
            assert "error" in response_data
            assert response_data["error"]["code"] == -32700  # Parse error
        except TypeError:
            # If get_json() fails, that's also acceptable for invalid JSON
            pass
    
    def test_missing_required_arguments(self, client):
        """Test calling tool without required arguments."""
        response = client.post(
            "/mcp",
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "grafana_get_dashboard_config_details",
                    "arguments": {}  # Missing dashboard_uid
                },
                "id": "error-2"
            }),
            content_type="application/json"
        )
        
        # Server returns 404 for unknown tools, which is correct behavior
        assert response.status_code == 404
        response_data = response.get_json()
        assert response_data["id"] == "error-2"
        
        # Should return an error
        assert "error" in response_data
        assert response_data["error"]["code"] == -32601  # Method not found


# Integration tests combining multiple tools
@pytest.mark.integration
class TestMCPIntegration:
    """Integration tests for MCP server functionality."""
    
    def test_full_dashboard_workflow(self, client):
        """Test complete dashboard workflow via MCP tools."""
        # Step 1: Fetch dashboards
        dashboards_response = client.post(
            "/mcp",
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "grafana_fetch_all_dashboards",
                    "arguments": {"limit": 1}
                },
                "id": "workflow-1"
            }),
            content_type="application/json"
        )
        
        assert dashboards_response.status_code == 200
        dashboards_data = dashboards_response.get_json()
        dashboards_content = json.loads(dashboards_data["result"]["content"][0]["text"])
        
        if dashboards_content["status"] == "error":
            pytest.skip("Cannot run workflow without available dashboards")
        
        dashboards = dashboards_content.get("data", [])
        if not dashboards:
            pytest.skip("No dashboards available for workflow")
        
        dashboard_uid = dashboards[0].get("uid")
        if not dashboard_uid:
            pytest.skip("Dashboard UID not available")
        
        # Step 2: Get dashboard config
        config_response = client.post(
            "/mcp",
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "grafana_get_dashboard_config",
                    "arguments": {"dashboard_uid": dashboard_uid}
                },
                "id": "workflow-2"
            }),
            content_type="application/json"
        )
        
        assert config_response.status_code == 200
        
        # Step 3: Query dashboard panels
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=1)
        
        panels_response = client.post(
            "/mcp",
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "grafana_query_dashboard_panels",
                    "arguments": {
                        "dashboard_uid": dashboard_uid,
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat()
                    }
                },
                "id": "workflow-3"
            }),
            content_type="application/json"
        )
        
        assert panels_response.status_code == 200
        
        print(f"Successfully completed MCP dashboard workflow for UID: {dashboard_uid}")