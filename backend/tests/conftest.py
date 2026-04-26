"""
Pytest configuration for backend tests.

This conftest.py mocks the limiter and other dependencies that require
external services (Redis) before any test modules are imported.
"""
import sys
from unittest.mock import MagicMock


# Create a proper mock limiter that can be used as a decorator
class MockLimiterClass:
    """Mock Limiter class that doesn't require Redis."""
    def __init__(self, key_func=None, storage_uri=None):
        pass
    
    def limit(self, *args, **kwargs):
        """Return a passthrough decorator."""
        def decorator(func):
            return func
        return decorator


def get_remote_address(request):
    """Mock get_remote_address function."""
    return "127.0.0.1"


# Create a module-like object that can be imported as 'from limiter import limiter'
class MockLimiterModule:
    """Mock the limiter module structure."""
    # The routes.users does: from limiter import limiter
    # So we need a 'limiter' attribute
    limiter = MockLimiterClass()
    Limiter = MockLimiterClass
    get_remote_address = staticmethod(get_remote_address)


# Replace the limiter module in sys.modules before anything else imports it
sys.modules['limiter'] = MockLimiterModule()
