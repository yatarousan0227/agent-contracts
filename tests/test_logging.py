"""Tests for logging utilities."""

import pytest
import logging
from unittest.mock import patch, MagicMock

from agent_contracts.utils.logging import (
    get_logger,
    configure_logging,
    get_structured_logger,
)


class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_logger_instance(self):
        """Test get_logger returns a Logger instance."""
        logger = get_logger("test")
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test"

    def test_default_name(self):
        """Test get_logger with default name."""
        logger = get_logger()
        
        assert logger.name == "agent_contracts"


class TestConfigureLogging:
    """Tests for configure_logging function."""

    def test_configures_logging(self):
        """Test configure_logging sets up logging."""
        # Just ensure it doesn't raise
        configure_logging(level=logging.DEBUG)

    def test_custom_format(self):
        """Test configure_logging with custom format."""
        configure_logging(
            level=logging.INFO,
            format_string="%(message)s",
        )


class TestGetStructuredLogger:
    """Tests for get_structured_logger function."""

    def test_returns_standard_logger_when_structlog_not_available(self):
        """Test returns standard logger when structlog not installed."""
        with patch('agent_contracts.utils.logging._HAS_STRUCTLOG', False):
            logger = get_structured_logger("test")
            
            assert isinstance(logger, logging.Logger)

    def test_returns_structlog_when_available(self):
        """Test returns structlog logger when available."""
        import importlib
        import sys
        import types

        import agent_contracts.utils.logging as logging_utils

        mock_logger = MagicMock()
        mock_structlog = types.SimpleNamespace()
        mock_structlog.get_logger = MagicMock(
            return_value=MagicMock(bind=MagicMock(return_value=mock_logger))
        )

        original = logging_utils
        sys.modules["structlog"] = mock_structlog
        try:
            reloaded = importlib.reload(logging_utils)
            logger = reloaded.get_structured_logger("test", foo="bar")
            assert logger is mock_logger
        finally:
            sys.modules.pop("structlog", None)
            importlib.reload(original)
