"""
Unit tests for provisioner.py
Uses unittest.mock to patch subprocess so no real system changes are made.
Run with: pytest tests/
"""
import json
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Make sure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import provisioner


# --- run_command ---

def test_run_command_success():
    with patch("provisioner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="output", returncode=0)
        result = provisioner.run_command("echo hello")
        assert result == "output"


def test_run_command_failure_returns_none():
    import subprocess
    with patch("provisioner.subprocess.run", side_effect=subprocess.CalledProcessError(1, "cmd", stderr="err")):
        result = provisioner.run_command("bad_command")
        assert result is None


def test_run_command_dry_run_skips_execution():
    with patch("provisioner.subprocess.run") as mock_run:
        result = provisioner.run_command("echo hello", dry_run=True)
        mock_run.assert_not_called()
        assert result == "[dry-run]"


# --- enforce_packages ---

def test_package_already_installed():
    report = []
    config = {"packages": ["vim"]}
    with patch("provisioner.run_command", return_value="vim installed"):
        provisioner.enforce_packages(config, dry_run=False, report=report)
    assert report[0]["status"] == "ok"


def test_package_installed_when_missing():
    report = []
    config = {"packages": ["vim"]}
    # First call (dpkg check) returns None, second call (apt-get) returns success
    with patch("provisioner.run_command", side_effect=[None, "ok"]):
        provisioner.enforce_packages(config, dry_run=False, report=report)
    assert report[0]["status"] == "installed"


def test_package_dry_run():
    report = []
    config = {"packages": ["vim"]}
    with patch("provisioner.run_command", return_value=None):
        provisioner.enforce_packages(config, dry_run=True, report=report)
    assert report[0]["status"] == "would_install"


# --- enforce_users ---

def test_user_already_exists():
    report = []
    config = {"users": ["alice"]}
    with patch("provisioner.run_command", return_value="1001"):
        provisioner.enforce_users(config, dry_run=False, report=report)
    assert report[0]["status"] == "ok"


def test_user_created_when_missing():
    report = []
    config = {"users": ["alice"]}
    with patch("provisioner.run_command", side_effect=[None, "ok"]):
        provisioner.enforce_users(config, dry_run=False, report=report)
    assert report[0]["status"] == "created"


def test_user_dry_run():
    report = []
    config = {"users": ["alice"]}
    with patch("provisioner.run_command", return_value=None):
        provisioner.enforce_users(config, dry_run=True, report=report)
    assert report[0]["status"] == "would_create"


# --- enforce_files ---

def test_file_permissions_set(tmp_path):
    report = []
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello")
    config = {"files": [{"path": str(test_file), "permissions": "0644"}]}
    with patch("provisioner.run_command", return_value="ok"):
        provisioner.enforce_files(config, dry_run=False, report=report)
    assert report[0]["status"] == "ok"


def test_file_skipped_when_not_found():
    report = []
    config = {"files": [{"path": "/nonexistent/file.txt", "permissions": "0644"}]}
    provisioner.enforce_files(config, dry_run=False, report=report)
    assert report[0]["status"] == "skipped_not_found"


# --- enforce_services ---

def test_service_already_running():
    report = []
    config = {"services": [{"name": "ssh", "state": "running", "enabled": True}]}
    with patch("provisioner.run_command", return_value="active"):
        provisioner.enforce_services(config, dry_run=False, report=report)
    assert report[0]["status"] == "ok"


def test_service_started_when_stopped():
    report = []
    config = {"services": [{"name": "ssh", "state": "running", "enabled": True}]}
    # First call is is-active check (returns inactive), rest are start/enable
    with patch("provisioner.run_command", side_effect=["inactive", "ok", "ok"]):
        provisioner.enforce_services(config, dry_run=False, report=report)
    assert report[0]["status"] == "started"


# --- save_report ---

def test_save_report_creates_json(tmp_path):
    with patch("provisioner.BASE_DIR", str(tmp_path)):
        provisioner.save_report([{"type": "package", "name": "vim", "status": "ok"}], dry_run=False)
        report_path = tmp_path / "compliance_report.json"
        assert report_path.exists()
        data = json.loads(report_path.read_text())
        assert data["dry_run"] is False
        assert data["results"][0]["name"] == "vim"
