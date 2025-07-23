import os
from typing import List, Optional

import pytest
import yaml

# Import your processor (adjust import path as needed)
from src.grafana_mcp_server.processor.grafana_processor import GrafanaApiProcessor

# Import evaluation utilities (optional)
try:
    from tests.utils import GrafanaResponseEvaluator
except ImportError:
    GrafanaResponseEvaluator = None


@pytest.fixture(scope="session")
def grafana_config():
    """
    Loads the Grafana configuration from the YAML file.
    """
    config_path = "src/grafana_mcp_server/config.yaml"  # Adjust path as needed
    if not os.path.exists(config_path):
        pytest.skip(f"Config file not found at {config_path}")

    with open(config_path) as f:
        config = yaml.safe_load(f)
    return config["grafana"]


@pytest.fixture(scope="session")
def grafana_processor(grafana_config):
    """
    Provides a GrafanaApiProcessor instance configured for live API testing.
    """
    return GrafanaApiProcessor(
        grafana_host=grafana_config["host"], grafana_api_key=grafana_config.get("api_key"), ssl_verify=str(grafana_config.get("ssl_verify", "true"))
    )


@pytest.fixture(scope="session")
def app():
    """
    Provides a test instance of the Flask application.
    """
    from src.grafana_mcp_server.mcp_server import app as flask_app

    flask_app.config.update({"TESTING": True})
    return flask_app


@pytest.fixture(scope="module")
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture(scope="session")
def openai_api_key():
    """Fixture to get the OpenAI API key."""
    config_path = os.path.join(os.path.dirname(__file__), "../src/grafana_mcp_server/config.yaml")
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError:
            pass  # Ignore malformed config

    key = config.get("openai", {}).get("api_key") if config else None
    return key


@pytest.fixture(scope="module")
def evaluator(openai_api_key):
    """Fixture to create a GrafanaResponseEvaluator instance for testing."""
    if GrafanaResponseEvaluator is None:
        pytest.skip("langevals not available - install with: pip install 'langevals[openai]'")

    if not openai_api_key:
        pytest.skip("OpenAI API key required for evaluation")

    # Use gpt-4o-mini for cost-effective testing
    return GrafanaResponseEvaluator(model="gpt-4o-mini")


@pytest.fixture(scope="module")
def mcp_client(openai_api_key, client):
    """Fixture to create an OpenAIMCPClient instance for testing."""
    if not openai_api_key:
        pytest.skip("OpenAI API key not available")

    from tests.clients.openai import OpenAIMCPClient

    mcp_client_instance = OpenAIMCPClient(
        test_client=client,
        openai_api_key=openai_api_key,
    )
    yield mcp_client_instance
    mcp_client_instance.close()


@pytest.fixture(scope="session", autouse=True)
def setup_environment():
    """Setup environment for testing."""
    config_path = "src/grafana_mcp_server/config.yaml"  # Adjust path
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
                openai_key = config.get("openai", {}).get("api_key")
                if openai_key:
                    os.environ["OPENAI_API_KEY"] = openai_key
        except yaml.YAMLError:
            pass

    yield


# Custom pytest markers for pass rate functionality
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "flaky: mark test as potentially flaky")
    config.addinivalue_line("markers", "pass_rate: specify minimum pass rate for test")


def assert_response_quality(
    prompt: str,
    response: str,
    evaluator,
    min_pass_rate: float = 0.8,
    specific_checks: Optional[List[str]] = None,
    required_checks: Optional[List[str]] = None,
):
    """
    Assert response quality using LLM evaluation.

    Args:
        prompt: The input prompt
        response: The generated response
        evaluator: Response evaluator instance
        min_pass_rate: Minimum pass rate required
        specific_checks: List of specific checks to run
        required_checks: List of required checks that must pass
    """
    if evaluator is None:
        pytest.skip("LLM evaluator not available")

    from tests.utils import assert_evaluation_passes, evaluate_response_quality

    results = evaluate_response_quality(prompt=prompt, response=response, evaluator=evaluator, specific_checks=specific_checks)

    assert_evaluation_passes(evaluation_results=results, min_pass_rate=min_pass_rate, required_checks=required_checks)
