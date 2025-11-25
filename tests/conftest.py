"""
Pytest configuration and shared fixtures.
"""

import pytest

# Enable async testing
pytest_plugins = ["pytest_asyncio"]


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Set test environment variables."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test@localhost/test")


@pytest.fixture
def sample_embedding():
    """Standard test embedding vector (OpenAI dimension)."""
    return [0.1] * 1536


@pytest.fixture
def sample_text():
    """Sample text for chunking tests."""
    return """# Test Document

This is the first paragraph with some content.

This is the second paragraph with different content.

## Section Two

More content in section two.
"""
