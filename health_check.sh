#!/bin/bash
set -euo pipefail

LOG="/var/log/state-provisioner.log"
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
DISK_THRESHOLD=90
CPU_THRESHOLD=85
MEM_THRESHOLD=90

log() {
    echo "$TIMESTAMP - $1 - $2" | tee -a "$LOG"
}

# --- Disk usage ---
DISK_USAGE=$(df / | awk 'NR==2 { print $5 }' | sed 's/%//')
if [ "$DISK_USAGE" -gt "$DISK_THRESHOLD" ]; then
    log "ALERT" "Disk usage is ${DISK_USAGE}% (threshold: ${DISK_THRESHOLD}%)"
else
    log "INFO" "Disk usage is nominal at ${DISK_USAGE}%"
fi

# --- CPU usage (1-second sample via /proc/stat) ---
read -r cpu user nice system idle iowait irq softirq _ < /proc/stat
total1=$((user + nice + system + idle + iowait + irq + softirq))
idle1=$idle
sleep 1
read -r cpu user nice system idle iowait irq softirq _ < /proc/stat
total2=$((user + nice + system + idle + iowait + irq + softirq))
idle2=$idle
cpu_used=$(( (1000 * (total2 - total1 - (idle2 - idle1)) / (total2 - total1) + 5) / 10 ))
if [ "$cpu_used" -gt "$CPU_THRESHOLD" ]; then
    log "ALERT" "CPU usage is ${cpu_used}% (threshold: ${CPU_THRESHOLD}%)"
else
    log "INFO" "CPU usage is nominal at ${cpu_used}%"
fi

# --- Memory usage ---
MEM_TOTAL=$(grep MemTotal /proc/meminfo | awk '{print $2}')
MEM_AVAILABLE=$(grep MemAvailable /proc/meminfo | awk '{print $2}')
MEM_USED=$(( (MEM_TOTAL - MEM_AVAILABLE) * 100 / MEM_TOTAL ))
if [ "$MEM_USED" -gt "$MEM_THRESHOLD" ]; then
    log "ALERT" "Memory usage is ${MEM_USED}% (threshold: ${MEM_THRESHOLD}%)"
else
    log "INFO" "Memory usage is nominal at ${MEM_USED}%"
fi

# --- Key services (reads from config.yaml if python3 available) ---
if command -v python3 &>/dev/null && command -v python3 &>/dev/null; then
    SERVICES=$(python3 -c "
import yaml, os
cfg = yaml.safe_load(open(os.path.join(os.path.dirname('$0'), 'config.yaml')))
for s in cfg.get('services', []):
    print(s['name'])
" 2>/dev/null || true)

    for svc in $SERVICES; do
        if systemctl is-active --quiet "$svc"; then
            log "INFO" "Service '$svc' is running"
        else
            log "ALERT" "Service '$svc' is NOT running"
        fi
    done
fi
