"""
Configuration file for pytest
"""

import pytest
import os


def pytest_configure(config):
    """Configure pytest"""
    # Ensure PG_DSN environment variable is set
    if "PG_DSN" not in os.environ:
        os.environ["PG_DSN"] = (
            "postgresql://memdb_user:memdb_pass@localhost:5432/memdb_test"
        )


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
