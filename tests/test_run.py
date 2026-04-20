"""
Tests for run.py launcher
"""
import pytest
import subprocess
from unittest.mock import patch, MagicMock


class TestInstallDependencies:
    """Test dependency installation logic"""

    @patch('builtins.input', return_value='')
    def test_installs_dependencies_when_missing(self, mock_input):
        """Test that install_dependencies returns False and prompts user when a dependency is missing"""
        import sys
        import run

        with patch.dict(sys.modules, {'requests': None}):
            result = run.install_dependencies('python.exe')

        assert result is False
        mock_input.assert_called_once()

    @patch('subprocess.run')
    def test_skips_install_when_all_present(self, mock_run):
        """Test that installation is skipped when all dependencies are present"""
        # This test assumes flask, pymysql, requests are installed
        import run

        # All modules should be importable
        try:
            import flask
            import pymysql
            import requests

            # Call install_dependencies
            run.install_dependencies('python.exe')

            # Should NOT have called pip install
            mock_run.assert_not_called()
        except ImportError:
            pytest.skip("Skipping test - dependencies not installed")
