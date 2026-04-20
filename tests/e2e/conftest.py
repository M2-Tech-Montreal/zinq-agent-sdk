"""Shared fixtures for E2E tests.

These tests run against the real dev server and require valid API keys.
Set the following environment variables before running:

    ZINQ_TEST_API_KEY  - A personal agent API key (zak_...)
    ZINQ_TEST_BIZ_KEY  - A marketplace admin API key (zbk_...)
    ZINQ_DEV_URL       - Dev server base URL (default: https://zinq-app.com/dev-api)
"""

from __future__ import annotations

import os
import uuid

import pytest

from zinq_agent import ZinqAgent, ZinqMarketplaceAdmin

DEV_BASE_URL = os.environ.get("ZINQ_DEV_URL", "https://zinq-app.com/dev-api")


def _unique_key(prefix: str = "e2e") -> str:
    """Generate a unique key to avoid collisions between test runs."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def agent():
    """Create a test personal agent, yield it, clean up after."""
    api_key = os.environ.get("ZINQ_TEST_API_KEY")
    if not api_key:
        pytest.skip("ZINQ_TEST_API_KEY not set")
    a = ZinqAgent(api_key=api_key, base_url=DEV_BASE_URL)
    yield a
    a.close()


@pytest.fixture
def admin():
    """Marketplace admin client."""
    biz_key = os.environ.get("ZINQ_TEST_BIZ_KEY")
    if not biz_key:
        pytest.skip("ZINQ_TEST_BIZ_KEY not set")
    a = ZinqMarketplaceAdmin(api_key=biz_key, base_url=DEV_BASE_URL)
    yield a
    a.close()


@pytest.fixture
def unique_key():
    """Return a factory for unique keys to avoid test collisions."""
    return _unique_key
