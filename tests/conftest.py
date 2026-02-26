import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "gpu: requires GPU and CUDA")
    config.addinivalue_line("markers", "ai_models: requires downloaded AI model weights")
    config.addinivalue_line("markers", "slow: tests that take > 30 seconds")
