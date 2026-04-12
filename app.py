import platform
import subprocess
import os
import json
import yaml
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response, stream_with_context

app = Flask(__name__)

IS_LINUX = platform.system() == "Linux"
LOG_FILE = "/var/log/state-provisioner.log"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.yaml")
REPORT_FILE = os.path.join(BASE_DIR, "compliance_report.json")

VALID_ACTIONS = {"provisioner", "provisioner_dry_run", "health_check"}
HISTORY_FILE = os.path.join(BASE_DIR, "run_history.json")

# Simple in-memory stats cache (refreshed every 10s)
_stats_cache = {"data": None, "ts": 0}


def record_run(action, success, line_count):
    """Append a run record to run_history.json."""
    try:
        history = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE) as f:
                history = json.load(f)
        history.append({
            "action": action,
            "success": success,
            "lines": line_count,
            "ts": datetime.now().isoformat(),
            "demo": DEMO_MODE,
        })
        # Keep last 50 runs
        with open(HISTORY_FILE, "w") as f:
            json.dump(history[-50:], f, indent=2)
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Demo mode: active when not on Linux OR when running without root.
# This lets the full UI work on Railway/Render/Vercel-like platforms and on
# any non-Linux machine, so it's explorable as a portfolio demo.
# ---------------------------------------------------------------------------
def _is_root():
    try:
        return os.geteuid() == 0
    except AttributeError:
        return False  # Windows has no geteuid

DEMO_MODE = not IS_LINUX or not _is_root()

import demo as demo_module  # always importable — no Linux deps


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_system_stats():
    global _stats_cache
    import time
    if DEMO_MODE:
        return demo_module.demo_stats()
    now = time.time()
    if _stats_cache["data"] and now - _stats_cache["ts"] < 10:
        return _stats_cache["data"]
    stats = {"is_linux": True, "demo": False}
    try:
        df = subprocess.run("df / --output=pcent | tail -1", shell=True, capture_output=True, text=True)
        stats["disk"] = df.stdout.strip().replace("%", "")
    except Exception:
        stats["disk"] = None
    try:
        mem = {}
        for line in open("/proc/meminfo"):
            k, v = line.split(":")
            mem[k.strip()] = int(v.split()[0])
        used = mem["MemTotal"] - mem["MemAvailable"]
        stats["mem"] = round(used / mem["MemTotal"] * 100)
    except Exception:
        stats["mem"] = None
    try:
        with open("/proc/uptime") as f:
            secs = float(f.read().split()[0])
        h, rem = divmod(int(secs), 3600)
        stats["uptime"] = f"{h}h {rem // 60}m"
    except Exception:
        stats["uptime"] = None
    try:
        stats["hostname"] = subprocess.run("hostname", shell=True, capture_output=True, text=True).stdout.strip()
    except Exception:
        stats["hostname"] = None
    _stats_cache = {"data": stats, "ts": time.time()}
    return stats


def read_logs(n=150):
    if DEMO_MODE:
        return demo_module.demo_logs(), True
    try:
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
        return "".join(lines[-n:]) or "(log is empty)", True
    except FileNotFoundError:
        return f"Log file not found: {LOG_FILE}", False
    except PermissionError:
        return f"Permission denied: {LOG_FILE}", False


def read_report():
    if DEMO_MODE:
        return demo_module.demo_report(), True
    try:
        with open(REPORT_FILE, "r") as f:
            return json.load(f), True
    except Exception:
        return None, False


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

def render(page, **kwargs):
    return render_template(
        "index.html",
        is_linux=IS_LINUX,
        demo_mode=DEMO_MODE,
        page=page,
        stats=get_system_stats(),
        **kwargs
    )


@app.route("/")
def index():
    return render("dashboard")


@app.route("/run")
def run_page():
    return render("run")


@app.route("/logs")
def logs_page():
    log_content, _ = read_logs()
    return render("logs", log_content=log_content)


@app.route("/report")
def report_page():
    report, found = read_report()
    return render("report", report=report, report_found=found)


@app.route("/config")
def config_page():
    try:
        with open(CONFIG_FILE) as f:
            config_content = f.read()
    except Exception as e:
        config_content = f"# Error reading config: {e}"
    return render("config", config_content=config_content)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.route("/api/stats")
def api_stats():
    return jsonify(get_system_stats())


@app.route("/api/run/<action>")
def api_run(action):
    if action not in VALID_ACTIONS:
        return jsonify({"error": "Invalid action"}), 400

    if DEMO_MODE:
        dry = action == "provisioner_dry_run"
        lines_fn = demo_module.health_check_lines if action == "health_check" \
                   else lambda: demo_module.provisioner_lines(dry_run=dry)

        def generate_demo():
            count = 0
            for line in lines_fn():
                count += 1
                yield f"data: {line}\n\n"
            record_run(action, True, count)

        return Response(stream_with_context(generate_demo()), mimetype="text/event-stream")

    if action == "provisioner":
        cmd = f"sudo python3 {BASE_DIR}/provisioner.py"
    elif action == "provisioner_dry_run":
        cmd = f"sudo python3 {BASE_DIR}/provisioner.py --dry-run"
    else:
        cmd = f"bash {BASE_DIR}/health_check.sh"

    def generate_real():
        count = 0
        try:
            proc = subprocess.Popen(
                cmd, shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1
            )
            for line in proc.stdout:
                count += 1
                yield f"data: {line.rstrip()}\n\n"
            proc.wait()
            record_run(action, proc.returncode == 0, count)
            yield f"data: [EXIT:{proc.returncode}]\n\n"
        except Exception as e:
            yield f"data: Error: {e}\n\n"

    return Response(stream_with_context(generate_real()), mimetype="text/event-stream")


@app.route("/api/logs")
def api_logs():
    content, ok = read_logs()
    return jsonify({"content": content, "ok": ok, "demo": DEMO_MODE})


@app.route("/api/report")
def api_report():
    report, found = read_report()
    return jsonify({"report": report, "found": found, "demo": DEMO_MODE})


@app.route("/api/save_config", methods=["POST"])
def api_save_config():
    data = request.get_json()
    content = data.get("content", "")
    try:
        yaml.safe_load(content)
        if not DEMO_MODE:
            with open(CONFIG_FILE, "w") as f:
                f.write(content)
        return jsonify({"ok": True, "demo": DEMO_MODE})
    except yaml.YAMLError as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/history")
def api_history():
    try:
        if DEMO_MODE:
            return jsonify({"history": demo_module.demo_history()})
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE) as f:
                return jsonify({"history": json.load(f)})
        return jsonify({"history": []})
    except Exception:
        return jsonify({"history": []})


@app.route("/api/clear_logs", methods=["POST"])
def api_clear_logs():
    if DEMO_MODE:
        return jsonify({"ok": True, "demo": True})
    try:
        open(LOG_FILE, "w").close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=False)
