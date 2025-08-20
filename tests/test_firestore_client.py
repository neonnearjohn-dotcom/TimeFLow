import os
import pytest
from unittest.mock import MagicMock, patch

from utils.firestore_client import create_firestore_client


def test_client_uses_env_path(monkeypatch):
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/tmp/cred.json")
    with (
        patch(
            "utils.firestore_client.service_account.Credentials.from_service_account_file",
            return_value=MagicMock(project_id="proj"),
        ) as mock_creds,
        patch("utils.firestore_client.firestore.Client", return_value="client") as mock_client,
    ):
        client = create_firestore_client()
        assert client == "client"
        mock_creds.assert_called_once()
        mock_client.assert_called_once()


def test_client_without_env(monkeypatch):
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    with patch("utils.firestore_client.firestore.Client", return_value="client") as mock_client:
        assert create_firestore_client() == "client"
        mock_client.assert_called_once()


def test_client_logs_error(monkeypatch, caplog):
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    with patch("utils.firestore_client.firestore.Client", side_effect=Exception("boom")):
        with caplog.at_level("ERROR"):
            assert create_firestore_client() is None
    assert "Firestore init failed" in caplog.text
