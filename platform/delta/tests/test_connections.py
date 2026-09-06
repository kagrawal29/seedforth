"""Tests for delta.connections module."""

import os
from unittest.mock import patch, MagicMock

import pytest

from delta import connections


class TestGetClient:
    """Tests for connections._get_client."""

    def test_returns_none_without_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("COMPOSIO_API_KEY", None)
            assert connections._get_client() is None

    def test_returns_client_with_api_key(self):
        with patch.dict(os.environ, {"COMPOSIO_API_KEY": "test-key"}):
            with patch("composio.Composio") as mock_cls:
                mock_cls.return_value = MagicMock()
                result = connections._get_client()
                assert result is not None
                mock_cls.assert_called_once_with(api_key="test-key")


# Patch the lazy import at module level
@pytest.fixture
def mock_composio():
    """Mock the Composio SDK client."""
    mock_client = MagicMock()
    with patch("delta.connections._get_client", return_value=mock_client):
        yield mock_client


@pytest.fixture
def mock_composio_none():
    """Mock _get_client returning None (no API key)."""
    with patch("delta.connections._get_client", return_value=None):
        yield


class TestInitiateConnection:
    """Tests for connections.initiate_connection."""

    def test_returns_redirect_url(self, mock_composio):
        entity = MagicMock()
        req = MagicMock()
        req.redirectUrl = "https://composio.dev/auth/hubspot"
        req.connectedAccountId = "conn-123"
        req.connectionStatus = "INITIATED"
        entity.initiate_connection.return_value = req
        mock_composio.get_entity.return_value = entity

        result = connections.initiate_connection("user-456", "hubspot")
        assert result["redirect_url"] == "https://composio.dev/auth/hubspot"
        assert result["connection_id"] == "conn-123"
        assert result["status"] == "INITIATED"
        entity.initiate_connection.assert_called_once_with(app_name="hubspot")

    def test_returns_error_on_exception(self, mock_composio):
        mock_composio.get_entity.side_effect = Exception("API error")
        result = connections.initiate_connection("user-456", "hubspot")
        assert "error" in result
        assert "API error" in result["error"]

    def test_returns_error_without_api_key(self, mock_composio_none):
        result = connections.initiate_connection("user-456", "hubspot")
        assert "error" in result
        assert "not configured" in result["error"]


class TestCheckStatus:
    """Tests for connections.check_status."""

    def test_returns_active(self, mock_composio):
        conn = MagicMock()
        conn.status = "ACTIVE"
        mock_composio.connected_accounts.get.return_value = conn

        assert connections.check_status("conn-123") == "ACTIVE"

    def test_returns_initiated(self, mock_composio):
        conn = MagicMock()
        conn.status = "INITIATED"
        mock_composio.connected_accounts.get.return_value = conn

        assert connections.check_status("conn-123") == "INITIATED"

    def test_returns_error_on_exception(self, mock_composio):
        mock_composio.connected_accounts.get.side_effect = Exception("Not found")
        assert connections.check_status("conn-123") == "ERROR"

    def test_returns_error_without_api_key(self, mock_composio_none):
        assert connections.check_status("conn-123") == "ERROR"


class TestListConnections:
    """Tests for connections.list_connections."""

    def test_returns_connections(self, mock_composio):
        conn1 = MagicMock()
        conn1.appName = "hubspot"
        conn1.status = "ACTIVE"
        conn1.id = "conn-1"
        conn2 = MagicMock()
        conn2.appName = "gmail"
        conn2.status = "INITIATED"
        conn2.id = "conn-2"

        entity = MagicMock()
        entity.get_connections.return_value = [conn1, conn2]
        mock_composio.get_entity.return_value = entity

        result = connections.list_connections("user-456")
        assert len(result) == 2
        assert result[0] == {"app": "hubspot", "status": "ACTIVE", "id": "conn-1"}
        assert result[1] == {"app": "gmail", "status": "INITIATED", "id": "conn-2"}

    def test_returns_empty_on_error(self, mock_composio):
        mock_composio.get_entity.side_effect = Exception("Error")
        assert connections.list_connections("user-456") == []

    def test_returns_empty_without_api_key(self, mock_composio_none):
        assert connections.list_connections("user-456") == []


class TestGetActiveConnection:
    """Tests for connections.get_active_connection."""

    def test_finds_active_connection(self, mock_composio):
        conn1 = MagicMock()
        conn1.appName = "hubspot"
        conn1.status = "ACTIVE"
        conn1.id = "conn-1"

        entity = MagicMock()
        entity.get_connections.return_value = [conn1]
        mock_composio.get_entity.return_value = entity

        assert connections.get_active_connection("user-456", "hubspot") == "conn-1"

    def test_returns_none_when_initiated(self, mock_composio):
        conn1 = MagicMock()
        conn1.appName = "hubspot"
        conn1.status = "INITIATED"
        conn1.id = "conn-1"

        entity = MagicMock()
        entity.get_connections.return_value = [conn1]
        mock_composio.get_entity.return_value = entity

        assert connections.get_active_connection("user-456", "hubspot") is None

    def test_returns_none_when_no_connections(self, mock_composio):
        entity = MagicMock()
        entity.get_connections.return_value = []
        mock_composio.get_entity.return_value = entity

        assert connections.get_active_connection("user-456", "hubspot") is None

    def test_case_insensitive_match(self, mock_composio):
        conn1 = MagicMock()
        conn1.appName = "HubSpot"
        conn1.status = "ACTIVE"
        conn1.id = "conn-1"

        entity = MagicMock()
        entity.get_connections.return_value = [conn1]
        mock_composio.get_entity.return_value = entity

        assert connections.get_active_connection("user-456", "hubspot") == "conn-1"
