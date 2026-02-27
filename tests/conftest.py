import pytest
import sys
from unittest.mock import MagicMock

def pytest_configure(config):
    config.addinivalue_line("markers", "gpu: requires GPU and CUDA")
    config.addinivalue_line("markers", "ai_models: requires downloaded AI model weights")
    config.addinivalue_line("markers", "slow: tests that take > 30 seconds")

@pytest.fixture(autouse=True)
def cleanup_sys_modules():
    # Capture initial sys.modules state if needed, but here we just want to remove mocks
    # that were added at top level of test files.
    # This is a bit risky but better than the current state.
    yield
    # No-op for now, better to fix the test files themselves.
