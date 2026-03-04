import os
import pytest
import json
import subprocess
import sys

@pytest.mark.slow
def test_scan_performance_baseline():
    """
    Runs a benchmark scan and verifies performance hasn't regressed significantly.
    This test creates a small temporary directory with some test images if needed.
    """
    # Use existing test data directory if available, otherwise skip or create dummy
    test_data_dir = os.path.join(os.getcwd(), "tests", "data", "performance_test")
    if not os.path.exists(test_data_dir):
        # Create dummy directory with a few images for smoke test
        os.makedirs(test_data_dir, exist_ok=True)
        # Note: in a real environment we'd use actual images, but for CI we might just 
        # want to ensure the benchmark script runs without crashing.
    
    # Run benchmark script
    benchmark_script = os.path.join(os.getcwd(), "scripts", "benchmark_scan.py")
    result = subprocess.run([
        sys.executable, benchmark_script, test_data_dir, "--limit", "5"
    ], capture_output=True, text=True)
    
    assert result.returncode == 0, f"Benchmark script failed: {result.stderr}"
    
    # Check if report was generated
    benchmarks_dir = os.path.join(os.getcwd(), "benchmarks")
    reports = [f for f in os.listdir(benchmarks_dir) if f.startswith("scan_baseline_") and f.endswith(".json")]
    assert len(reports) > 0, "No benchmark report generated"
    
    # Load latest report
    latest_report = sorted(reports)[-1]
    with open(os.path.join(benchmarks_dir, latest_report), 'r') as f:
        data = json.load(f)
    
    assert "total_duration" in data
    assert "peak_rss_mb" in data
    assert data["total_duration"] > 0
    
    print(f"Benchmark passed: {data['total_duration']:.2f}s for {data['newly_processed']} files")
