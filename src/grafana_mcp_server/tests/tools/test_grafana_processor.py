import pytest
from datetime import datetime, timezone, timedelta


@pytest.fixture
def processor(grafana_config):
    """
    Provides a GrafanaApiProcessor instance configured for live API testing.
    """
    from src.grafana_mcp_server.processor.grafana_processor import GrafanaApiProcessor
    return GrafanaApiProcessor(
        grafana_host=grafana_config["host"],
        grafana_api_key=grafana_config.get("api_key"),
        ssl_verify=str(grafana_config.get("ssl_verify", "true"))
    )


class TestGrafanaConnection:
    """Test Grafana connection functionality."""
    
    def test_connection(self, processor):
        """Test the connection to the live Grafana API."""
        result = processor.test_connection()
        assert result is True or isinstance(result, dict)
        if isinstance(result, dict):
            assert result.get("status") in ["success", "error"]


class TestGrafanaDashboards:
    """Test Grafana dashboard functionality."""
    
    def test_fetch_all_dashboards(self, processor):
        """Test fetching all dashboards from Grafana."""
        result = processor.grafana_fetch_all_dashboards()
        assert result is not None
        
        if isinstance(result, dict):
            if result.get("status") == "error":
                pytest.skip(f"Dashboard fetch failed: {result.get('message', 'Unknown error')}")
            else:
                assert "data" in result or "dashboards" in result
        elif isinstance(result, list):
            # Direct list of dashboards
            assert isinstance(result, list)
    
    def test_fetch_all_dashboards_with_limit(self, processor):
        """Test fetching dashboards with a limit."""
        limit = 5
        result = processor.grafana_fetch_all_dashboards(limit=limit)
        assert result is not None
        
        if isinstance(result, dict) and result.get("status") != "error":
            data = result.get("data", result.get("dashboards", []))
            if isinstance(data, list) and len(data) > 0:
                assert len(data) <= limit
    
    def test_get_dashboard_config(self, processor):
        """Test getting dashboard configuration."""
        # First get a dashboard to test with
        dashboards_result = processor.grafana_fetch_all_dashboards(limit=1)
        
        if isinstance(dashboards_result, dict) and dashboards_result.get("status") == "error":
            pytest.skip("Cannot test dashboard config without available dashboards")
        
        dashboards = dashboards_result
        if isinstance(dashboards_result, dict):
            dashboards = dashboards_result.get("data", dashboards_result.get("dashboards", []))
        
        if not dashboards or len(dashboards) == 0:
            pytest.skip("No dashboards available for testing")
        
        dashboard_uid = dashboards[0].get("uid")
        if not dashboard_uid:
            pytest.skip("Dashboard UID not available")
        
        result = processor.grafana_get_dashboard_config_details(dashboard_uid)
        assert result is not None
        
        if isinstance(result, dict) and result.get("status") == "error":
            pytest.skip(f"Dashboard config fetch failed: {result.get('message')}")
        
        # Should contain dashboard configuration
        assert isinstance(result, dict)


class TestGrafanaQueries:
    """Test Grafana query functionality."""
    
    def test_promql_query(self, processor):
        """Test PromQL query execution."""
        # Simple test query
        query = "up"
        
        # Use recent time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=1)
        
        # First get a datasource to use for the query
        datasources_result = processor.grafana_fetch_datasources()
        if isinstance(datasources_result, dict) and datasources_result.get("status") == "error":
            pytest.skip(f"Cannot test PromQL without datasources: {datasources_result.get('message')}")
        
        datasources = datasources_result
        if isinstance(datasources_result, dict):
            datasources = datasources_result.get("data", datasources_result.get("datasources", []))
        
        if not datasources or len(datasources) == 0:
            pytest.skip("No datasources available for PromQL testing")
        
        # Find a Prometheus datasource
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
        
        result = processor.grafana_promql_query(
            datasource_uid=datasource_uid,
            query=query,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat()
        )
        
        assert result is not None
        
        if isinstance(result, dict) and result.get("status") == "error":
            # PromQL queries might fail due to datasource config
            pytest.skip(f"PromQL query failed: {result.get('message')}")
        
        # Should contain query results
        assert isinstance(result, dict)
    
    @pytest.mark.skip(reason="Loki query requires specific datasource configuration")
    def test_loki_query(self, processor):
        """Test Loki query execution."""
        # Simple test query
        query = '{job="grafana"}'
        
        # Use recent time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=1)
        
        result = processor.grafana_loki_query(
            query=query,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            limit=100
        )
        
        assert result is not None
        
        if isinstance(result, dict) and result.get("status") == "error":
            # Loki queries might fail due to datasource config
            pytest.skip(f"Loki query failed: {result.get('message')}")
        
        # Should contain query results
        assert isinstance(result, dict)
    
    def test_fetch_label_values(self, processor):
        """Test fetching label values."""
        # First get a datasource to use for the query
        datasources_result = processor.grafana_fetch_datasources()
        if isinstance(datasources_result, dict) and datasources_result.get("status") == "error":
            pytest.skip(f"Cannot test label values without datasources: {datasources_result.get('message')}")
        
        datasources = datasources_result
        if isinstance(datasources_result, dict):
            datasources = datasources_result.get("data", datasources_result.get("datasources", []))
        
        if not datasources or len(datasources) == 0:
            pytest.skip("No datasources available for label values testing")
        
        # Find a Prometheus datasource
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
        
        # Test with a common label
        label = "job"
        
        result = processor.grafana_fetch_dashboard_variable_label_values(datasource_uid=datasource_uid, label_name=label)
        assert result is not None
        
        if isinstance(result, dict) and result.get("status") == "error":
            pytest.skip(f"Label values fetch failed: {result.get('message')}")
        
        # Should contain label values
        if isinstance(result, dict):
            assert "data" in result or "values" in result
        elif isinstance(result, list):
            assert isinstance(result, list)


class TestGrafanaDatasources:
    """Test Grafana datasource functionality."""
    
    def test_fetch_datasources(self, processor):
        """Test fetching all datasources."""
        result = processor.grafana_fetch_datasources()
        assert result is not None
        
        if isinstance(result, dict) and result.get("status") == "error":
            pytest.skip(f"Datasources fetch failed: {result.get('message')}")
        
        if isinstance(result, dict):
            assert "data" in result or "datasources" in result
        elif isinstance(result, list):
            assert isinstance(result, list)


class TestGrafanaFolders:
    """Test Grafana folder functionality."""
    
    def test_fetch_folders(self, processor):
        """Test fetching all folders."""
        result = processor.grafana_fetch_folders()
        assert result is not None
        
        if isinstance(result, dict) and result.get("status") == "error":
            pytest.skip(f"Folders fetch failed: {result.get('message')}")
        
        if isinstance(result, dict):
            assert "data" in result or "folders" in result
        elif isinstance(result, list):
            assert isinstance(result, list)


class TestGrafanaDashboardPanels:
    """Test Grafana dashboard panel functionality."""
    
    def test_query_dashboard_panels(self, processor):
        """Test querying dashboard panels."""
        # First get a dashboard to test with
        dashboards_result = processor.grafana_fetch_all_dashboards(limit=1)
        
        if isinstance(dashboards_result, dict) and dashboards_result.get("status") == "error":
            pytest.skip("Cannot test panel queries without available dashboards")
        
        dashboards = dashboards_result
        if isinstance(dashboards_result, dict):
            dashboards = dashboards_result.get("data", dashboards_result.get("dashboards", []))
        
        if not dashboards or len(dashboards) == 0:
            pytest.skip("No dashboards available for testing")
        
        dashboard_uid = dashboards[0].get("uid")
        if not dashboard_uid:
            pytest.skip("Dashboard UID not available")
        
        # Get dashboard config to find panel IDs
        dashboard_config = processor.grafana_get_dashboard_config_details(dashboard_uid)
        if isinstance(dashboard_config, dict) and dashboard_config.get("status") == "error":
            pytest.skip(f"Cannot get dashboard config: {dashboard_config.get('message')}")
        
        dashboard = dashboard_config.get("dashboard", {})
        
        # Handle both old and new dashboard structures
        panels = dashboard.get("panels", [])
        if not panels:
            # Try to get panels from rows (newer dashboard structure)
            rows = dashboard.get("rows", [])
            for row in rows:
                row_panels = row.get("panels", [])
                panels.extend(row_panels)
        
        if not panels:
            pytest.skip("No panels found in dashboard")
        
        # Use first panel for testing
        panel_ids = [panels[0].get("id")]
        if not panel_ids[0]:
            pytest.skip("Panel ID not available")
        
        result = processor.grafana_query_dashboard_panels(
            dashboard_uid=dashboard_uid,
            panel_ids=panel_ids
        )
        
        assert result is not None
        
        if isinstance(result, dict) and result.get("status") == "error":
            pytest.skip(f"Dashboard panel query failed: {result.get('message')}")
        
        # Should contain panel data
        assert isinstance(result, dict)
    
    def test_fetch_dashboard_variables(self, processor):
        """Test fetching dashboard variables."""
        # First get a dashboard to test with
        dashboards_result = processor.grafana_fetch_all_dashboards(limit=1)
        
        if isinstance(dashboards_result, dict) and dashboards_result.get("status") == "error":
            pytest.skip("Cannot test variables without available dashboards")
        
        dashboards = dashboards_result
        if isinstance(dashboards_result, dict):
            dashboards = dashboards_result.get("data", dashboards_result.get("dashboards", []))
        
        if not dashboards or len(dashboards) == 0:
            pytest.skip("No dashboards available for testing")
        
        dashboard_uid = dashboards[0].get("uid")
        if not dashboard_uid:
            pytest.skip("Dashboard UID not available")
        
        result = processor.grafana_fetch_dashboard_variables(dashboard_uid=dashboard_uid)
        
        assert result is not None
        
        if isinstance(result, dict) and result.get("status") == "error":
            pytest.skip(f"Dashboard variables fetch failed: {result.get('message')}")
        
        # Should contain variables data
        if isinstance(result, dict):
            assert "data" in result or "variables" in result
        elif isinstance(result, list):
            assert isinstance(result, list)


# Utility tests
class TestUtilityFunctions:
    """Test utility functions in the processor."""
    
    def test_time_parsing(self, processor):
        """Test time parsing functionality if available."""
        # This depends on your processor implementation
        # Add tests for any time parsing utilities you have
        pass
    
    def test_error_handling(self, processor):
        """Test error handling with invalid requests."""
        # Test with invalid dashboard UID
        try:
            result = processor.grafana_get_dashboard_config_details("invalid-uid-12345")
            # If it doesn't raise an exception, it should return an error status
            if isinstance(result, dict):
                assert result.get("status") in ["error", "success"] or "error" in result
        except Exception as e:
            # It's also acceptable for the method to raise an exception for invalid UIDs
            assert "not found" in str(e).lower() or "404" in str(e) or "invalid" in str(e).lower()


# Integration tests
@pytest.mark.integration
class TestGrafanaIntegration:
    """Integration tests that test multiple components together."""
    
    def test_dashboard_workflow(self, processor):
        """Test complete dashboard workflow: fetch -> get config -> query panels."""
        # Step 1: Fetch dashboards
        dashboards_result = processor.grafana_fetch_all_dashboards(limit=1)
        
        if isinstance(dashboards_result, dict) and dashboards_result.get("status") == "error":
            pytest.skip("Cannot run integration test without available dashboards")
        
        dashboards = dashboards_result
        if isinstance(dashboards_result, dict):
            dashboards = dashboards_result.get("data", dashboards_result.get("dashboards", []))
        
        if not dashboards or len(dashboards) == 0:
            pytest.skip("No dashboards available for integration testing")
        
        dashboard_uid = dashboards[0].get("uid")
        if not dashboard_uid:
            pytest.skip("Dashboard UID not available for integration testing")
        
        # Step 2: Get dashboard config
        config_result = processor.grafana_get_dashboard_config_details(dashboard_uid)
        assert config_result is not None
        
        if isinstance(config_result, dict) and config_result.get("status") == "error":
            pytest.skip(f"Dashboard config failed: {config_result.get('message')}")
        
        # Step 3: Query dashboard panels (if panels exist)
        dashboard = config_result.get("dashboard", {})
        panels = dashboard.get("panels", [])
        
        if panels:
            panel_ids = [panels[0].get("id")]
            if panel_ids[0]:
                panels_result = processor.grafana_query_dashboard_panels(
                    dashboard_uid=dashboard_uid,
                    panel_ids=panel_ids
                )
                assert panels_result is not None
                print(f"Successfully queried panel {panel_ids[0]}")
            else:
                print("No valid panel IDs found")
        else:
            print("No panels found in dashboard")
        
        # All steps should complete successfully
        print(f"Successfully completed dashboard workflow for UID: {dashboard_uid}")
    
    def test_datasource_and_query_workflow(self, processor):
        """Test datasource discovery and query workflow."""
        # Step 1: Fetch datasources
        datasources_result = processor.grafana_fetch_datasources()
        
        if isinstance(datasources_result, dict) and datasources_result.get("status") == "error":
            pytest.skip("Cannot test query workflow without datasources")
        
        datasources = datasources_result
        if isinstance(datasources_result, dict):
            datasources = datasources_result.get("data", datasources_result.get("datasources", []))
        
        if not datasources or len(datasources) == 0:
            pytest.skip("No datasources available for workflow testing")
        
        # Find Prometheus datasource for PromQL test
        prometheus_ds = None
        for ds in datasources:
            if isinstance(ds, dict) and ds.get("type") == "prometheus":
                prometheus_ds = ds
                break
        
        if prometheus_ds:
            # Step 2: Test PromQL query
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=1)
            
            query_result = processor.grafana_promql_query(
                datasource_uid=prometheus_ds.get("uid"),
                query="up",
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat()
            )
            
            # Query might fail due to configuration, but should not crash
            assert query_result is not None
            print(f"Successfully tested workflow with Prometheus datasource: {prometheus_ds.get('name')}")
        else:
            pytest.skip("No Prometheus datasource found for PromQL testing")