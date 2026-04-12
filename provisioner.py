import yaml
import subprocess
import logging
import os
import json
import argparse
from datetime import datetime

LOG_FILE = "/var/log/state-provisioner.log"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.yaml")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)


def run_command(command, dry_run=False):
    """Run a shell command. In dry-run mode, just print what would run."""
    if dry_run:
        logging.info(f"[DRY-RUN] Would run: {command}")
        return "[dry-run]"
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {command} | Error: {e.stderr}")
        return None


def enforce_packages(config, dry_run, report):
    for pkg in config.get('packages', []):
        check = run_command(f"dpkg -l | grep -w {pkg}")
        if not check or check == "[dry-run]":
            if dry_run:
                logging.info(f"[DRY-RUN] Would install package: {pkg}")
                report.append({"type": "package", "name": pkg, "status": "would_install"})
            else:
                logging.info(f"Installing package: {pkg}")
                run_command(f"apt-get install -y {pkg}")
                report.append({"type": "package", "name": pkg, "status": "installed"})
        else:
            logging.info(f"Package already present: {pkg}")
            report.append({"type": "package", "name": pkg, "status": "ok"})


def enforce_users(config, dry_run, report):
    for user in config.get('users', []):
        check = run_command(f"id -u {user}")
        if check is None:
            if dry_run:
                logging.info(f"[DRY-RUN] Would create user: {user}")
                report.append({"type": "user", "name": user, "status": "would_create"})
            else:
                logging.info(f"Creating user: {user}")
                run_command(f"useradd -m {user}")
                report.append({"type": "user", "name": user, "status": "created"})
        else:
            logging.info(f"User already exists: {user}")
            report.append({"type": "user", "name": user, "status": "ok"})


def enforce_files(config, dry_run, report):
    for file_data in config.get('files', []):
        path = file_data['path']
        perms = file_data['permissions']
        if os.path.exists(path):
            if dry_run:
                logging.info(f"[DRY-RUN] Would set permissions {perms} on {path}")
                report.append({"type": "file", "path": path, "permissions": perms, "status": "would_chmod"})
            else:
                logging.info(f"Setting permissions {perms} on {path}")
                run_command(f"chmod {perms} {path}")
                report.append({"type": "file", "path": path, "permissions": perms, "status": "ok"})
        else:
            logging.warning(f"File not found, skipping: {path}")
            report.append({"type": "file", "path": path, "permissions": perms, "status": "skipped_not_found"})


def enforce_services(config, dry_run, report):
    """Ensure systemd services are in the desired state."""
    for svc in config.get('services', []):
        name = svc['name']
        desired_state = svc.get('state', 'running')
        enabled = svc.get('enabled', True)

        # Check if service is currently active
        active = run_command(f"systemctl is-active {name}")
        is_running = active == "active"

        if desired_state == "running" and not is_running:
            if dry_run:
                logging.info(f"[DRY-RUN] Would start service: {name}")
                report.append({"type": "service", "name": name, "status": "would_start"})
            else:
                logging.info(f"Starting service: {name}")
                run_command(f"systemctl start {name}")
                report.append({"type": "service", "name": name, "status": "started"})
        elif desired_state == "stopped" and is_running:
            if dry_run:
                logging.info(f"[DRY-RUN] Would stop service: {name}")
                report.append({"type": "service", "name": name, "status": "would_stop"})
            else:
                logging.info(f"Stopping service: {name}")
                run_command(f"systemctl stop {name}")
                report.append({"type": "service", "name": name, "status": "stopped"})
        else:
            logging.info(f"Service {name} already in desired state ({desired_state}).")
            report.append({"type": "service", "name": name, "status": "ok"})

        # Handle enabled/disabled
        if enabled:
            run_command(f"systemctl enable {name}", dry_run)
        else:
            run_command(f"systemctl disable {name}", dry_run)


def enforce_cron_jobs(config, dry_run, report):
    """Add cron jobs if they aren't already present."""
    for job in config.get('cron_jobs', []):
        name = job['name']
        user = job.get('user', 'root')
        schedule = job['schedule']
        command = job['command']
        cron_line = f"{schedule} {command}"

        # Check if this exact cron line already exists for the user
        existing = run_command(f"crontab -l -u {user} 2>/dev/null | grep -F '{command}'")
        if existing:
            logging.info(f"Cron job already exists: {name}")
            report.append({"type": "cron", "name": name, "status": "ok"})
        else:
            if dry_run:
                logging.info(f"[DRY-RUN] Would add cron job: {name} -> {cron_line}")
                report.append({"type": "cron", "name": name, "status": "would_add"})
            else:
                logging.info(f"Adding cron job: {name}")
                # Append to existing crontab
                run_command(f'(crontab -l -u {user} 2>/dev/null; echo "{cron_line}") | crontab -u {user} -')
                report.append({"type": "cron", "name": name, "status": "added"})


def save_report(report, dry_run):
    """Write a JSON compliance report next to this script."""
    report_path = os.path.join(BASE_DIR, "compliance_report.json")
    output = {
        "generated_at": datetime.now().isoformat(),
        "dry_run": dry_run,
        "results": report
    }
    with open(report_path, "w") as f:
        json.dump(output, f, indent=2)
    logging.info(f"Compliance report saved to {report_path}")


def enforce_state(dry_run=False):
    with open(CONFIG_FILE, 'r') as f:
        config = yaml.safe_load(f)

    if dry_run:
        logging.info("=== DRY-RUN MODE — no changes will be made ===")

    report = []
    enforce_packages(config, dry_run, report)
    enforce_users(config, dry_run, report)
    enforce_files(config, dry_run, report)
    enforce_services(config, dry_run, report)
    enforce_cron_jobs(config, dry_run, report)
    save_report(report, dry_run)

    # Print a summary table to stdout
    print("\n--- Compliance Report ---")
    for item in report:
        label = item.get('name') or item.get('path')
        print(f"  [{item['type']:8}] {label:30} -> {item['status']}")
    print("-------------------------\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Light-Ansible provisioner")
    parser.add_argument(
        "--dry-run", "--check",
        action="store_true",
        help="Show what would change without making any changes (like ansible --check)"
    )
    args = parser.parse_args()

    if os.geteuid() != 0:
        print("Please run this script with sudo!")
    else:
        enforce_state(dry_run=args.dry_run)
