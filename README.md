# Light-Ansible

A lightweight Linux system state provisioner inspired by Ansible's idempotent enforcement model. Declare your desired system state in `config.yaml` and run the provisioner to enforce it — packages, users, file permissions, services, and cron jobs.

## What it does

- Installs packages via `apt-get` if not already present
- Creates Linux users if they don't exist
- Enforces file permissions with `chmod`
- Starts/stops and enables/disables systemd services
- Adds cron jobs if not already scheduled
- Generates a structured JSON compliance report after each run
- Supports `--dry-run` / `--check` mode — shows what *would* change without touching the system (same concept as `ansible --check`)

## Project structure

```
light-ansible/
├── config.yaml              # Desired system state — edit this to change what gets enforced
├── provisioner.py           # Core logic — reads config.yaml and enforces state
├── runner.sh                # Entry point — checks for Python, then runs provisioner.py
├── health_check.sh          # Monitors disk, CPU, memory, and service status
├── app.py                   # Flask web UI
├── templates/index.html     # UI template
├── compliance_report.json   # Generated after each provisioner run (gitignored)
└── tests/
    └── test_provisioner.py  # Unit tests (pytest)
```

## ⚠ Linux Requirement

This tool **only works on Linux** (Debian/Ubuntu recommended). It relies on:

- `apt-get` / `dpkg` — package management
- `useradd` — user creation
- `systemctl` — service management
- `chmod` — file permissions
- `/proc/meminfo`, `/proc/stat`, `/proc/uptime` — system metrics

**It will not work on macOS or Windows natively.** If you're on Windows, use [WSL (Windows Subsystem for Linux)](https://learn.microsoft.com/en-us/windows/wsl/install) to run it.

> **Note for Vercel / serverless platforms:** This app cannot be deployed to Vercel, Netlify, or any serverless platform. Those environments don't allow subprocess execution, `sudo`, or persistent filesystem access. You need a real Linux server.

## Deployment

To host this on a Linux server (e.g. a DigitalOcean Droplet, AWS EC2, or any Ubuntu VPS):

```bash
# 1. SSH into your Linux server
ssh user@your-server-ip

# 2. Clone the repo
git clone https://github.com/SimeonVarg/Light-Ansible.git
cd light-ansible

# 3. Set up the environment
python3 -m venv venv
source venv/bin/activate
pip install flask pyyaml

# 4. Run (use sudo since the provisioner needs root)
sudo venv/bin/python3 app.py
```

For a production setup, run Flask behind a reverse proxy like nginx with gunicorn:

```bash
pip install gunicorn
sudo gunicorn -w 2 -b 0.0.0.0:5000 app:app
```

## Setup

```bash
# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install flask pyyaml pytest
```

## Usage

### Web UI
```bash
python3 app.py
# Open http://127.0.0.1:5000
```

### CLI — run provisioner
```bash
sudo bash runner.sh
```

### CLI — dry run (no changes made)
```bash
sudo bash runner.sh --dry-run
```

### CLI — health check
```bash
bash health_check.sh
```

### Run tests
```bash
pytest tests/
```

## Configuration

Edit `config.yaml` to declare desired state:

```yaml
packages:
  - vim
  - git

users:
  - deploy_user

files:
  - path: "/tmp/compliance_check.txt"
    permissions: "0644"

services:
  - name: ssh
    state: running   # running | stopped
    enabled: true

cron_jobs:
  - name: "nightly log cleanup"
    user: root
    schedule: "0 2 * * *"
    command: "find /var/log -name '*.gz' -mtime +30 -delete"
```

## Logs

All provisioner and health check output is written to `/var/log/state-provisioner.log`.

The provisioner must be run as root (`sudo`) since it manages system-level resources.
