"""
Tests for run.py launcher
"""
import pytest
import subprocess
from unittest.mock import patch, MagicMock


class TestInstallDependencies:
    """Test dependency installation logic"""

    @patch('subprocess.run')
    def test_installs_dependencies_when_missing(self, mock_run):
        """Test that dependencies are installed when requests is missing"""
        # Mock requests as not installed
        import sys
        old_import = sys.modules.get('requests')

        def mock_import(name, *args, **kwargs):
            if name == 'requests':
                raise ImportError("No module named 'requests'")
            return old_import

        with patch('builtins.__import__', side_effect=mock_import):
            # Simulate missing requests
            if 'requests' in sys.modules:
                del sys.modules['requests']

            # Import run module fresh
            import importlib
            import run

            # Reload to get fresh import
            importlib.reload(run)

            # Call install_dependencies
            run.install_dependencies('python.exe')

            # Should have called pip install
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert 'pip' in args
            assert 'install' in args
            assert '-e' in args
            assert '.' in args

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
