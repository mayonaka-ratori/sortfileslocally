import pytest
import sys
from unittest.mock import MagicMock

def pytest_configure(config):
    config.addinivalue_line("markers", "gpu: requires GPU and CUDA")
    config.addinivalue_line("markers", "ai_models: requires downloaded AI model weights")
    config.addinivalue_line("markers", "slow: tests that take > 30 seconds")

@pytest.fixture(autouse=True)
def cleanup_app_overrides():
    yield
    # Safely try to clear overrides if the module is loaded
    if "server.main" in sys.modules:
        try:
            from server.main import app
            app.dependency_overrides.clear()
        except:
            pass

@pytest.fixture(autouse=True)
def cleanup_sys_modules():
    # Save a snapshot of sys.modules before the test
    initial_modules = sys.modules.copy()
    yield
    # Restore sys.modules after the test
    # First, remove any NEWLY added modules
    current_modules = list(sys.modules.keys())
    for mod in current_modules:
        if mod not in initial_modules:
            del sys.modules[mod]
    # Then, restore original module objects
    sys.modules.update(initial_modules)
