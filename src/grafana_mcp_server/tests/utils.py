"""
Utility functions for robust LLM evaluation using langevals.
"""
from typing import Dict, Any, List, Optional
import pandas as pd

try:
    from langevals import expect
    from langevals_langevals.llm_boolean import (
        CustomLLMBooleanEvaluator,
        CustomLLMBooleanSettings,
    )
    LANGEVALS_AVAILABLE = True
except ImportError:
    LANGEVALS_AVAILABLE = False
    CustomLLMBooleanEvaluator = None
    CustomLLMBooleanSettings = None


class GrafanaResponseEvaluator:
    """Evaluator for Grafana MCP Server responses."""
    
    def __init__(self, model: str = "gpt-4o"):
        if not LANGEVALS_AVAILABLE:
            raise ImportError("langevals not available. Install with: pip install 'langevals[openai]'")
        self.model = model
    
    def is_helpful_response(self, prompt: str, response: str) -> bool:
        """Check if response is helpful and addresses the prompt."""
        evaluator = CustomLLMBooleanEvaluator(
            settings=CustomLLMBooleanSettings(
                prompt="Is this response helpful and does it address the user's question effectively?",
                model=self.model,
            )
        )
        try:
            expect(input=prompt, output=response).to_pass(evaluator)
            return True
        except AssertionError:
            return False
    
    def is_structured_response(self, prompt: str, response: str) -> bool:
        """Check if response is well-structured and clear."""
        evaluator = CustomLLMBooleanEvaluator(
            settings=CustomLLMBooleanSettings(
                prompt="Is this response well-structured, clear, and easy to understand?",
                model=self.model,
            )
        )
        try:
            expect(input=prompt, output=response).to_pass(evaluator)
            return True
        except AssertionError:
            return False
    
    def contains_connection_status(self, prompt: str, response: str) -> bool:
        """Check if response contains connection test information."""
        evaluator = CustomLLMBooleanEvaluator(
            settings=CustomLLMBooleanSettings(
                prompt="Does the response contain connection status information with details like 'success', 'host', and connection verification?",
                model=self.model,
            )
        )
        try:
            expect(input=prompt, output=response).to_pass(evaluator)
            return True
        except AssertionError:
            return False
    
    def contains_dashboard_info(self, prompt: str, response: str) -> bool:
        """Check if response contains dashboard information."""
        evaluator = CustomLLMBooleanEvaluator(
            settings=CustomLLMBooleanSettings(
                prompt="Does the response contain specific information about Grafana dashboards, such as dashboard titles, IDs, or configurations?",
                model=self.model,
            )
        )
        try:
            expect(input=prompt, output=response).to_pass(evaluator)
            return True
        except AssertionError:
            return False
    
    def contains_promql_query_result(self, prompt: str, response: str) -> bool:
        """Check if response contains PromQL query results."""
        evaluator = CustomLLMBooleanEvaluator(
            settings=CustomLLMBooleanSettings(
                prompt="Does the response contain PromQL query results with metrics data, timestamps, or values?",
                model=self.model,
            )
        )
        try:
            expect(input=prompt, output=response).to_pass(evaluator)
            return True
        except AssertionError:
            return False
    
    def contains_loki_query_result(self, prompt: str, response: str) -> bool:
        """Check if response contains Loki query results."""
        evaluator = CustomLLMBooleanEvaluator(
            settings=CustomLLMBooleanSettings(
                prompt="Does the response contain Loki query results with log data, timestamps, or log entries?",
                model=self.model,
            )
        )
        try:
            expect(input=prompt, output=response).to_pass(evaluator)
            return True
        except AssertionError:
            return False
    
    def contains_datasource_info(self, prompt: str, response: str) -> bool:
        """Check if response contains datasource information."""
        evaluator = CustomLLMBooleanEvaluator(
            settings=CustomLLMBooleanSettings(
                prompt="Does the response contain information about Grafana datasources, such as datasource names, types, or configurations?",
                model=self.model,
            )
        )
        try:
            expect(input=prompt, output=response).to_pass(evaluator)
            return True
        except AssertionError:
            return False
    
    def contains_folder_info(self, prompt: str, response: str) -> bool:
        """Check if response contains folder information."""
        evaluator = CustomLLMBooleanEvaluator(
            settings=CustomLLMBooleanSettings(
                prompt="Does the response contain information about Grafana folders, such as folder names, IDs, or hierarchies?",
                model=self.model,
            )
        )
        try:
            expect(input=prompt, output=response).to_pass(evaluator)
            return True
        except AssertionError:
            return False
    
    def contains_label_values(self, prompt: str, response: str) -> bool:
        """Check if response contains label values."""
        evaluator = CustomLLMBooleanEvaluator(
            settings=CustomLLMBooleanSettings(
                prompt="Does the response contain label values or metric labels from Grafana queries?",
                model=self.model,
            )
        )
        try:
            expect(input=prompt, output=response).to_pass(evaluator)
            return True
        except AssertionError:
            return False


def create_test_dataset(test_cases: List[Dict[str, Any]]) -> pd.DataFrame:
    """Create a pandas DataFrame from test cases for evaluation."""
    return pd.DataFrame(test_cases)


def evaluate_response_quality(
    prompt: str, 
    response: str, 
    evaluator: GrafanaResponseEvaluator,
    specific_checks: Optional[List[str]] = None
) -> Dict[str, bool]:
    """
    Evaluate response quality using multiple criteria.
    
    Args:
        prompt: The input prompt/question
        response: The generated response
        evaluator: GrafanaResponseEvaluator instance
        specific_checks: List of specific checks to run
    
    Returns:
        Dictionary with evaluation results
    """
    if not LANGEVALS_AVAILABLE:
        return {"evaluation_skipped": True}
    
    results = {}
    
    # Always check these basic qualities
    results["is_helpful"] = evaluator.is_helpful_response(prompt, response)
    results["is_structured"] = evaluator.is_structured_response(prompt, response)
    
    # Run specific checks if provided
    if specific_checks:
        for check in specific_checks:
            if check == "connection_status":
                results["contains_connection"] = evaluator.contains_connection_status(prompt, response)
            elif check == "dashboard_info":
                results["contains_dashboards"] = evaluator.contains_dashboard_info(prompt, response)
            elif check == "promql_query_result":
                results["contains_promql_result"] = evaluator.contains_promql_query_result(prompt, response)
            elif check == "loki_query_result":
                results["contains_loki_result"] = evaluator.contains_loki_query_result(prompt, response)
            elif check == "datasource_info":
                results["contains_datasources"] = evaluator.contains_datasource_info(prompt, response)
            elif check == "folder_info":
                results["contains_folders"] = evaluator.contains_folder_info(prompt, response)
            elif check == "label_values":
                results["contains_label_values"] = evaluator.contains_label_values(prompt, response)
    
    return results


def assert_evaluation_passes(
    evaluation_results: Dict[str, bool], 
    min_pass_rate: float = 0.8,
    required_checks: Optional[List[str]] = None
) -> None:
    """
    Assert that evaluation results meet quality standards.
    
    Args:
        evaluation_results: Dictionary of evaluation results
        min_pass_rate: Minimum pass rate (0.0 to 1.0)
        required_checks: List of checks that must pass
    """
    if not LANGEVALS_AVAILABLE or evaluation_results.get("evaluation_skipped"):
        import pytest
        pytest.skip("LLM evaluation not available")
    
    # Check required checks first
    if required_checks:
        for check in required_checks:
            if not evaluation_results.get(check, False):
                raise AssertionError(f"Required check '{check}' failed")
    
    # Calculate overall pass rate
    total_checks = len(evaluation_results)
    passed_checks = sum(1 for result in evaluation_results.values() if result)
    pass_rate = passed_checks / total_checks if total_checks > 0 else 0.0
    
    if pass_rate < min_pass_rate:
        failed_checks = [check for check, result in evaluation_results.items() if not result]
        raise AssertionError(
            f"Pass rate {pass_rate:.2f} below minimum {min_pass_rate:.2f}. "
            f"Failed checks: {failed_checks}"
        )
