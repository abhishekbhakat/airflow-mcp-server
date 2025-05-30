"""Tests for main CLI functionality."""

import os
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from airflow_mcp_server import main


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


def test_main_help(runner):
    """Test main command help."""
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "MCP server for Airflow" in result.output
    assert "--safe" in result.output
    assert "--unsafe" in result.output
    assert "--base-url" in result.output
    assert "--auth-token" in result.output


def test_main_missing_config(runner):
    """Test main with missing configuration."""
    result = runner.invoke(main, [])
    assert result.exit_code == 1
    assert "Configuration error" in result.output


def test_main_with_cli_args(runner):
    """Test main with CLI arguments."""
    with patch("airflow_mcp_server.serve_unsafe") as mock_serve:
        mock_serve.return_value = None
        with patch("asyncio.run") as mock_asyncio:
            result = runner.invoke(main, ["--base-url", "http://localhost:8080", "--auth-token", "test-token"])

            # Should not exit with error
            assert result.exit_code == 0
            mock_asyncio.assert_called_once()


def test_main_safe_mode(runner):
    """Test main in safe mode."""
    with patch("airflow_mcp_server.serve_safe") as mock_serve_safe:
        mock_serve_safe.return_value = None
        with patch("asyncio.run") as mock_asyncio:
            result = runner.invoke(main, ["--safe", "--base-url", "http://localhost:8080", "--auth-token", "test-token"])

            assert result.exit_code == 0
            mock_asyncio.assert_called_once()


def test_main_unsafe_mode(runner):
    """Test main in unsafe mode."""
    with patch("airflow_mcp_server.serve_unsafe") as mock_serve_unsafe:
        mock_serve_unsafe.return_value = None
        with patch("asyncio.run") as mock_asyncio:
            result = runner.invoke(main, ["--unsafe", "--base-url", "http://localhost:8080", "--auth-token", "test-token"])

            assert result.exit_code == 0
            mock_asyncio.assert_called_once()


def test_main_conflicting_modes(runner):
    """Test main with conflicting safe/unsafe flags."""
    result = runner.invoke(main, ["--safe", "--unsafe", "--base-url", "http://localhost:8080", "--auth-token", "test-token"])

    assert result.exit_code == 2  # Click usage error
    assert "mutually exclusive" in result.output


def test_main_env_variables(runner):
    """Test main with environment variables."""
    env_vars = {"AIRFLOW_BASE_URL": "http://localhost:8080", "AUTH_TOKEN": "env-token"}

    with patch.dict(os.environ, env_vars):
        with patch("airflow_mcp_server.serve_unsafe") as mock_serve:
            mock_serve.return_value = None
            with patch("asyncio.run") as mock_asyncio:
                result = runner.invoke(main, [])

                assert result.exit_code == 0
                mock_asyncio.assert_called_once()


def test_main_env_overrides_cli(runner):
    """Test that environment variables override CLI args (current behavior)."""
    env_vars = {"AIRFLOW_BASE_URL": "http://env:8080", "AUTH_TOKEN": "env-token"}

    with patch.dict(os.environ, env_vars):
        with patch("airflow_mcp_server.AirflowConfig") as mock_config:
            with patch("airflow_mcp_server.serve_unsafe"):
                with patch("asyncio.run"):
                    result = runner.invoke(main, ["--base-url", "http://cli:8080", "--auth-token", "cli-token"])

                    assert result.exit_code == 0
                    # Environment variables take precedence in current implementation
                    mock_config.assert_called_once_with(base_url="http://env:8080", auth_token="env-token")


def test_main_verbose_logging(runner):
    """Test verbose logging options."""
    with patch("airflow_mcp_server.serve_unsafe"):
        with patch("asyncio.run"):
            with patch("logging.basicConfig") as mock_logging:
                result = runner.invoke(
                    main,
                    [
                        "-vv",  # Very verbose
                        "--base-url",
                        "http://localhost:8080",
                        "--auth-token",
                        "test-token",
                    ],
                )

                assert result.exit_code == 0
                # Check that logging was configured
                mock_logging.assert_called_once()
                call_args = mock_logging.call_args
                # Just verify that stream parameter was passed (Click uses different stderr)
                assert "stream" in call_args[1]
