#!/usr/bin/env python3
"""
Test Runner with OpenTelemetry Integration
Runs all tests with comprehensive telemetry tracking and reporting.
"""

import sys
import os
import pytest
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.telemetry import get_telemetry


def run_tests_with_telemetry():
    """Run all tests with OpenTelemetry tracking"""
    
    # Initialize telemetry
    telemetry = get_telemetry(
        service_name="epstein-test-suite",
        enable_console_export=True,
        enable_otlp_export=False
    )
    
    print("=" * 70)
    print("EPSTEIN MULTI-AGENT SYSTEM - TEST SUITE")
    print("=" * 70)
    print(f"Test execution started at: {datetime.now().isoformat()}")
    print()
    
    # Create span for entire test run
    with telemetry.create_span("test_suite_execution", {
        "test.suite": "epstein-multi-agent-system",
        "test.timestamp": datetime.now().isoformat()
    }):
        
        # Run pytest with coverage
        pytest_args = [
            "tests/",
            "-v",
            "--tb=short",
            "--cov=agents",
            "--cov=tools",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-report=json:coverage.json",
            "-p", "no:warnings"
        ]
        
        print("Running tests with coverage...")
        print()
        
        exit_code = pytest.main(pytest_args)
        
        # Get telemetry metrics
        metrics = telemetry.get_agent_metrics()
        
        print()
        print("=" * 70)
        print("TEST EXECUTION SUMMARY")
        print("=" * 70)
        print(f"Exit Code: {exit_code}")
        print(f"Test execution completed at: {datetime.now().isoformat()}")
        
        # Print telemetry metrics
        print()
        print("TELEMETRY METRICS:")
        print(json.dumps(metrics, indent=2))
        
        # Save metrics to file
        metrics_file = f"test_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        print(f"\nMetrics saved to: {metrics_file}")
        
        # Check if coverage report was generated
        if os.path.exists("coverage.json"):
            with open("coverage.json", 'r') as f:
                coverage_data = json.load(f)
                total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)
                print(f"\nTotal Coverage: {total_coverage:.2f}%")
        
        print()
        print("=" * 70)
        
        # Shutdown telemetry
        telemetry.shutdown()
        
        return exit_code


if __name__ == "__main__":
    exit_code = run_tests_with_telemetry()
    sys.exit(exit_code)
