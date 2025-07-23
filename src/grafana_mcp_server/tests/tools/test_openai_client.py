import pytest
from tests.clients.openai import OpenAIMCPClient
from tests.conftest import assert_response_quality

# Mark all tests in this file as 'integration'
pytestmark = pytest.mark.integration

# Test data for parameterized testing
test_models = ["gpt-4.1"]
connection_queries = [
    "Test the connection to Grafana.",
    "Check Grafana connection status.",
    "Verify connection to Grafana.",
]
dashboard_queries = [
    "Fetch all available dashboards from Grafana.",
    "Show me the dashboards.",
    "List all dashboards available.",
    "Get me information about Grafana dashboards.",
]
query_tests = [
    "Run a simple PromQL query to check if services are up.",
    "Execute a PromQL query: up",
    "Query Grafana metrics using PromQL.",
]
datasource_queries = [
    "What datasources are available in Grafana?",
    "Show me all the datasources.",
    "List Grafana datasources.",
]


@pytest.fixture(scope="module")
def mcp_client(openai_api_key, client):
    """Fixture to create an OpenAIMCPClient instance for testing."""
    if not openai_api_key:
        pytest.skip("OpenAI API key not available")

    mcp_client_instance = OpenAIMCPClient(
        test_client=client,
        openai_api_key=openai_api_key,
        model="gpt-4.1"
    )
    yield mcp_client_instance
    mcp_client_instance.close()


class TestOpenAIIntegration:
    """Test OpenAI integration with MCP server."""
    
    def test_openai_client_initialization(self, mcp_client):
        """Test that OpenAI client initializes correctly."""
        assert mcp_client is not None
        assert mcp_client.model == "gpt-4.1"
        assert len(mcp_client.available_tools) > 0
    
    @pytest.mark.parametrize("model", ["gpt-4.1"])
    @pytest.mark.parametrize("query", connection_queries)
    @pytest.mark.flaky(max_runs=3)
    def test_connection_queries(self, mcp_client, evaluator, model, query):
        """Test connection-related queries using LLM evaluation."""
        messages = [{"role": "user", "content": query}]
        response = mcp_client.chat(messages=messages, model=model)
        
        assert response is not None
        assert len(response) > 0
        
        if evaluator:
            assert_response_quality(
                prompt=query,
                response=response,
                evaluator=evaluator,
                min_pass_rate=0.7,
                specific_checks=["connection_status"],
                required_checks=["is_helpful"]
            )
        
        print(f"Connection query successful: {query}")
    
    @pytest.mark.parametrize("model", ["gpt-4.1"])
    @pytest.mark.parametrize("query", dashboard_queries)
    @pytest.mark.flaky(max_runs=3)
    def test_dashboard_queries(self, mcp_client, evaluator, model, query):
        """Test dashboard-related queries using LLM evaluation."""
        messages = [{"role": "user", "content": query}]
        response = mcp_client.chat(messages=messages, model=model)
        
        assert response is not None
        assert len(response) > 0
        
        if evaluator:
            assert_response_quality(
                prompt=query,
                response=response,
                evaluator=evaluator,
                min_pass_rate=0.7,
                specific_checks=["dashboard_info"], 
                required_checks=["is_helpful"]
            )
        
        print(f"Dashboard query successful: {query}")
    
    @pytest.mark.parametrize("model", ["gpt-4.1"])
    @pytest.mark.parametrize("query", query_tests)
    @pytest.mark.flaky(max_runs=3)
    def test_promql_queries(self, mcp_client, evaluator, model, query):
        """Test PromQL-related queries using LLM evaluation."""
        messages = [{"role": "user", "content": query}]
        response = mcp_client.chat(messages=messages, model=model)
        
        assert response is not None
        assert len(response) > 0
        
        # Use LLM evaluation if available
        if evaluator:
            assert_response_quality(
                prompt=query,
                response=response,
                evaluator=evaluator,
                min_pass_rate=0.6,
                specific_checks=["promql_query_result"],
                required_checks=["is_helpful"]
            )
        
        print(f"PromQL query successful: {query}")
    
    @pytest.mark.parametrize("model", ["gpt-4.1"])
    @pytest.mark.parametrize("query", datasource_queries)
    @pytest.mark.flaky(max_runs=3)
    def test_datasource_queries(self, mcp_client, evaluator, model, query):
        """Test datasource-related queries using LLM evaluation."""
        messages = [{"role": "user", "content": query}]
        response = mcp_client.chat(messages=messages, model=model)
        
        assert response is not None
        assert len(response) > 0
        
        # Use LLM evaluation if available
        if evaluator:
            assert_response_quality(
                prompt=query,
                response=response,
                evaluator=evaluator,
                min_pass_rate=0.7,
                specific_checks=["datasource_info"],
                required_checks=["is_helpful"]
            )
        
        print(f"Datasource query successful: {query}")


class TestComplexScenarios:
    """Test complex multi-step scenarios."""
    
    def test_dashboard_exploration_workflow(self, mcp_client, evaluator):
        """Test a complex dashboard exploration workflow."""
        query = (
            "I want to explore Grafana dashboards. First, show me what dashboards are available, "
            "then pick one and show me its configuration, and finally tell me about the datasources."
        )
        
        messages = [{"role": "user", "content": query}]
        response = mcp_client.chat(messages=messages)
        
        assert response is not None
        assert len(response) > 0
        
        # This should involve multiple tool calls
        assert "dashboard" in response.lower()
        
        # Use LLM evaluation if available
        if evaluator:
            assert_response_quality(
                prompt=query,
                response=response,
                evaluator=evaluator,
                min_pass_rate=0.6,
                specific_checks=["dashboard_info", "datasource_info"],
                required_checks=["is_helpful"]
            )
        
        print("Complex dashboard exploration workflow completed successfully")
    
    def test_monitoring_setup_guidance(self, mcp_client, evaluator):
        """Test guidance for monitoring setup."""
        query = (
            "I'm setting up monitoring for my application. Can you help me understand "
            "what's available in Grafana? Show me the datasources and some example dashboards."
        )
        
        messages = [{"role": "user", "content": query}]
        response = mcp_client.chat(messages=messages)
        
        assert response is not None
        assert len(response) > 0
        
        # Use LLM evaluation if available
        if evaluator:
            assert_response_quality(
                prompt=query,
                response=response,
                evaluator=evaluator,
                min_pass_rate=0.6,
                specific_checks=["dashboard_info", "datasource_info"],
                required_checks=["is_helpful"]
            )
        
        print("Monitoring setup guidance completed successfully")
    
    def test_troubleshooting_scenario(self, mcp_client, evaluator):
        """Test troubleshooting scenario."""
        query = (
            "I'm trying to troubleshoot an issue with my application. "
            "Can you help me run some basic queries to check if my services are up and running?"
        )
        
        messages = [{"role": "user", "content": query}]
        response = mcp_client.chat(messages=messages)
        
        assert response is not None
        assert len(response) > 0
        
        # Use LLM evaluation if available
        if evaluator:
            assert_response_quality(
                prompt=query,
                response=response,
                evaluator=evaluator,
                min_pass_rate=0.6,
                specific_checks=["promql_query_result"],
                required_checks=["is_helpful"]
            )
        
        print("Troubleshooting scenario completed successfully")


class TestErrorHandling:
    """Test error handling in OpenAI integration."""
    
    def test_invalid_queries(self, mcp_client):
        """Test handling of invalid or nonsensical queries."""
        invalid_queries = [
            "Make me a sandwich",
            "What's the weather like?",
            "Solve world hunger",
        ]
        
        for query in invalid_queries:
            messages = [{"role": "user", "content": query}]
            response = mcp_client.chat(messages=messages)
            
            # Should still return a response, even if it's explaining limitations
            assert response is not None
            assert len(response) > 0
            
            print(f"Handled invalid query appropriately: {query}")
    
    def test_partial_tool_failures(self, mcp_client):
        """Test handling when some tools might fail."""
        query = (
            "Show me all dashboards and then run a PromQL query for a metric that probably doesn't exist: "
            "non_existent_metric_12345"
        )
        
        messages = [{"role": "user", "content": query}]
        response = mcp_client.chat(messages=messages)
        
        # Should handle partial failures gracefully
        assert response is not None
        assert len(response) > 0
        
        print("Handled partial tool failures appropriately")


class TestPerformance:
    """Test performance aspects of OpenAI integration."""
    
    @pytest.mark.timeout(30)  # Should complete within 30 seconds
    def test_response_time(self, mcp_client):
        """Test that responses are generated within reasonable time."""
        query = "What dashboards are available in Grafana?"
        
        messages = [{"role": "user", "content": query}]
        response = mcp_client.chat(messages=messages)
        
        assert response is not None
        assert len(response) > 0
        
        print("Response generated within acceptable time limit")
    
    def test_multiple_sequential_queries(self, mcp_client):
        """Test handling multiple sequential queries."""
        queries = [
            "Test the Grafana connection.",
            "Show me available dashboards.",
            "What datasources are configured?",
        ]
        
        responses = []
        for query in queries:
            messages = [{"role": "user", "content": query}]
            response = mcp_client.chat(messages=messages)
            responses.append(response)
        
        # All queries should succeed
        for i, response in enumerate(responses):
            assert response is not None
            assert len(response) > 0
            print(f"Sequential query {i+1} completed successfully")


# Utility function for manual testing
def manual_test_conversation(mcp_client, queries: list):
    """
    Utility function for manual testing of conversation flows.
    
    Args:
        mcp_client: OpenAI MCP client instance
        queries: List of queries to test
    """
    for i, query in enumerate(queries, 1):
        print(f"\n--- Query {i}: {query} ---")
        
        messages = [{"role": "user", "content": query}]
        response = mcp_client.chat(messages=messages)
        
        print(f"Response: {response}")
        print("-" * 50)