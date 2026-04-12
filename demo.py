"""
demo.py — Simulated output for non-Linux / non-root environments.

When Light-Ansible is deployed to a platform like Railway or Render (or run
on a non-Linux machine), it can't actually execute apt-get, useradd, systemctl,
etc. This module returns realistic fake output so the full UI is explorable
as a portfolio demo without needing a root Linux environment.
"""

import json
import time
from datetime import datetime

# Simulated config that mirrors config.yaml
DEMO_CONFIG = {
    "packages": ["vim", "git", "curl"],
    "users": ["simeon_test", "deploy_user"],
    "files": [{"path": "/tmp/compliance_check.txt", "permissions": "0644"}],
    "services": [{"name": "ssh", "state": "running", "enabled": True}],
    "cron_jobs": [{"name": "nightly log cleanup", "schedule": "0 2 * * *",
                   "command": "find /var/log -name '*.gz' -mtime +30 -delete"}],
}


def provisioner_lines(dry_run=False):
    """Yield simulated provisioner output lines with small delays."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = "[DRY-RUN] " if dry_run else ""

    yield f"{now} - INFO - {'=== DRY-RUN MODE — no changes will be made ===' if dry_run else 'Starting provisioner...'}"
    time.sleep(0.3)

    # Packages
    for pkg in DEMO_CONFIG["packages"]:
        time.sleep(0.2)
        yield f"{now} - INFO - {prefix}Package already present: {pkg}"

    # Users
    for user in DEMO_CONFIG["users"]:
        time.sleep(0.2)
        if dry_run:
            yield f"{now} - INFO - [DRY-RUN] Would create user: {user}"
        else:
            yield f"{now} - INFO - Creating user: {user}"

    # Files
    for f in DEMO_CONFIG["files"]:
        time.sleep(0.15)
        if dry_run:
            yield f"{now} - INFO - [DRY-RUN] Would set permissions {f['permissions']} on {f['path']}"
        else:
            yield f"{now} - INFO - Setting permissions {f['permissions']} on {f['path']}"

    # Services
    for svc in DEMO_CONFIG["services"]:
        time.sleep(0.2)
        yield f"{now} - INFO - Service {svc['name']} already in desired state (running)."

    # Cron
    for job in DEMO_CONFIG["cron_jobs"]:
        time.sleep(0.15)
        if dry_run:
            yield f"{now} - INFO - [DRY-RUN] Would add cron job: {job['name']} -> {job['schedule']} {job['command']}"
        else:
            yield f"{now} - INFO - Cron job already exists: {job['name']}"

    time.sleep(0.2)
    yield f"{now} - INFO - Compliance report saved to /app/compliance_report.json"
    yield ""
    yield "--- Compliance Report ---"

    statuses = {
        "packages": "ok",
        "users": "would_create" if dry_run else "created",
        "files": "would_chmod" if dry_run else "ok",
        "services": "ok",
        "cron_jobs": "would_add" if dry_run else "ok",
    }

    for pkg in DEMO_CONFIG["packages"]:
        yield f"  [package ] {pkg:<30} -> {statuses['packages']}"
    for user in DEMO_CONFIG["users"]:
        yield f"  [user    ] {user:<30} -> {statuses['users']}"
    for f in DEMO_CONFIG["files"]:
        yield f"  [file    ] {f['path']:<30} -> {statuses['files']}"
    for svc in DEMO_CONFIG["services"]:
        yield f"  [service ] {svc['name']:<30} -> {statuses['services']}"
    for job in DEMO_CONFIG["cron_jobs"]:
        yield f"  [cron    ] {job['name']:<30} -> {statuses['cron_jobs']}"

    yield "-------------------------"
    yield "[EXIT:0]"


def health_check_lines():
    """Yield simulated health check output."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    time.sleep(0.3)
    yield f"{now} - INFO - Disk usage is nominal at 34%"
    time.sleep(0.4)
    yield f"{now} - INFO - CPU usage is nominal at 12%"
    time.sleep(0.4)
    yield f"{now} - INFO - Memory usage is nominal at 41%"
    time.sleep(0.3)
    yield f"{now} - INFO - Service 'ssh' is running"
    yield "[EXIT:0]"


def demo_report(dry_run=False):
    """Return a realistic compliance report dict."""
    user_status = "would_create" if dry_run else "created"
    file_status = "would_chmod" if dry_run else "ok"
    cron_status = "would_add" if dry_run else "ok"

    results = []
    for pkg in DEMO_CONFIG["packages"]:
        results.append({"type": "package", "name": pkg, "status": "ok"})
    for user in DEMO_CONFIG["users"]:
        results.append({"type": "user", "name": user, "status": user_status})
    for f in DEMO_CONFIG["files"]:
        results.append({"type": "file", "path": f["path"], "permissions": f["permissions"], "status": file_status})
    for svc in DEMO_CONFIG["services"]:
        results.append({"type": "service", "name": svc["name"], "status": "ok"})
    for job in DEMO_CONFIG["cron_jobs"]:
        results.append({"type": "cron", "name": job["name"], "status": cron_status})

    return {
        "generated_at": datetime.now().isoformat(),
        "dry_run": dry_run,
        "demo": True,
        "results": results,
    }


def demo_logs():
    """Return a block of realistic log lines."""
    lines = []
    base = datetime.now()
    entries = [
        (0,   "INFO",  "Starting provisioner..."),
        (1,   "INFO",  "Package already present: vim"),
        (2,   "INFO",  "Package already present: git"),
        (3,   "INFO",  "Package already present: curl"),
        (4,   "INFO",  "Creating user: simeon_test"),
        (5,   "INFO",  "Creating user: deploy_user"),
        (6,   "INFO",  "Setting permissions 0644 on /tmp/compliance_check.txt"),
        (7,   "INFO",  "Service ssh already in desired state (running)."),
        (8,   "INFO",  "Cron job already exists: nightly log cleanup"),
        (9,   "INFO",  "Compliance report saved to /app/compliance_report.json"),
        (60,  "INFO",  "Health Check: Disk usage is nominal (Current: 34%)"),
        (61,  "INFO",  "Health Check: CPU usage is nominal at 12%"),
        (62,  "INFO",  "Health Check: Memory usage is nominal at 41%"),
        (63,  "INFO",  "Service 'ssh' is running"),
        (120, "INFO",  "Starting provisioner..."),
        (121, "INFO",  "Package already present: vim"),
        (122, "INFO",  "Package already present: git"),
        (123, "INFO",  "Package already present: curl"),
        (124, "INFO",  "User simeon_test already exists."),
        (125, "INFO",  "User deploy_user already exists."),
        (126, "INFO",  "Setting permissions 0644 on /tmp/compliance_check.txt"),
        (127, "INFO",  "Service ssh already in desired state (running)."),
        (128, "INFO",  "Compliance report saved to /app/compliance_report.json"),
    ]
    for offset, level, msg in entries:
        from datetime import timedelta
        ts = (base - timedelta(seconds=300 - offset)).strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"{ts} - {level} - {msg}")
    return "\n".join(lines)


def demo_stats():
    """Return fake but realistic system stats."""
    return {
        "is_linux": True,
        "disk": "34",
        "mem": 41,
        "uptime": "3h 22m",
        "hostname": "light-ansible-demo",
        "demo": True,
    }


def demo_history():
    """Return a fake run history for demo mode."""
    from datetime import datetime, timedelta
    base = datetime.now()
    entries = [
        {"action": "provisioner_dry_run", "success": True,  "lines": 18, "demo": True},
        {"action": "health_check",         "success": True,  "lines": 4,  "demo": True},
        {"action": "provisioner",          "success": True,  "lines": 22, "demo": True},
        {"action": "provisioner_dry_run",  "success": True,  "lines": 18, "demo": True},
        {"action": "health_check",         "success": True,  "lines": 4,  "demo": True},
    ]
    result = []
    for i, e in enumerate(reversed(entries)):
        e["ts"] = (base - timedelta(minutes=i * 14 + 3)).isoformat()
        result.append(e)
    return list(reversed(result))
