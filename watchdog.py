import sqlite3
import subprocess
import sys
import time

import requests

HEALTH_URL = "http://127.0.0.1:5000/health"
CHECK_EVERY = 5     # seconds between checks
FAIL_LIMIT = 3      # failed checks in a row before restarting
DB_FILE = "keepalive.db"


def is_healthy():
    try:
        return requests.get(HEALTH_URL, timeout=2).status_code == 200
    except requests.RequestException:
        return False


def start_service():
    return subprocess.Popen([sys.executable, "app.py"])


def stop_service(process):
    if process.poll() is None:          # still running
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def wait_until_healthy(max_wait=30):
    start = time.time()
    while time.time() - start < max_wait:
        if is_healthy():
            return True
        time.sleep(0.5)
    return False


def setup_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            detected_at TEXT NOT NULL,
            reason TEXT NOT NULL,
            recovery_seconds REAL
        )
    """)
    conn.commit()
    return conn


def main():
    conn = setup_db()
    process = start_service()
    if not wait_until_healthy():
        print("Service did not start. Check app.py.")
        stop_service(process)
        conn.close()
        return

    print("Service is up. Watching", HEALTH_URL, "(Ctrl+C to stop)")
    fails = 0
    try:
        while True:
            if is_healthy():
                fails = 0
            else:
                fails += 1
                print(f"Check failed ({fails}/{FAIL_LIMIT})")
                if fails >= FAIL_LIMIT:
                    detected = time.strftime("%Y-%m-%d %H:%M:%S")
                    started = time.time()
                    stop_service(process)
                    process = start_service()
                    recovered = wait_until_healthy()
                    seconds = round(time.time() - started, 1) if recovered else None
                    conn.execute(
                        "INSERT INTO incidents (detected_at, reason, recovery_seconds) VALUES (?, ?, ?)",
                        (detected, f"health check failed {FAIL_LIMIT} times in a row", seconds),
                    )
                    conn.commit()
                    print("Restarted. Recovery seconds:", seconds)
                    fails = 0
            time.sleep(CHECK_EVERY)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        stop_service(process)
        conn.close()


if __name__ == "__main__":
    main()