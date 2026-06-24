import subprocess
import threading
import time
import sys
import os
import signal
import importlib
from datetime import datetime

PACKAGES = {
    "telebot": "pyTelegramBotAPI",
    "telegram": "python-telegram-bot",
    "pyrogram": "pyrogram",
    "requests": "requests",
}


def ensure_dependencies():
    for mod, pkg in PACKAGES.items():
        try:
            importlib.import_module(mod)
        except ImportError:
            print(f"[SETUP] Installing missing package: {pkg}...", flush=True)
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", pkg, "--quiet"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            print(f"[SETUP] {pkg} installed.", flush=True)

BOTS = [
    "Bomb spam.py",
    "Color Buttons Bot.py",
    "PyGuard.py",
    "Remove clothes.py",
    "TokPilot.py",
    "Wolf Contests.py",
    "Wolf Roulette.py",
]

PYTHON = sys.executable
LOG_LOCK = threading.Lock()


def log(bot_name, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with LOG_LOCK:
        print(f"[{timestamp}] [{bot_name}] {message}", flush=True)


def monitor_bot(bot_file):
    while True:
        log(bot_file, "Starting...")
        process = subprocess.Popen(
            [PYTHON, bot_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        log(bot_file, f"Started (PID: {process.pid})")

        def print_output():
            for line in iter(process.stdout.readline, ""):
                if line:
                    log(bot_file, line.rstrip())

        output_thread = threading.Thread(target=print_output, daemon=True)
        output_thread.start()

        process.wait()
        log(bot_file, f"Crashed/Stopped (exit code: {process.returncode})")
        log(bot_file, "Restarting in 5 seconds...")
        time.sleep(5)


def main():
    ensure_dependencies()
    log("MAIN", f"Starting {len(BOTS)} bots...")
    log("MAIN", "-" * 50)

    threads = []
    for bot_file in BOTS:
        t = threading.Thread(target=monitor_bot, args=(bot_file,), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(2)

    log("MAIN", f"All {len(BOTS)} bots are running. Monitoring active.")
    log("MAIN", "Press Ctrl+C to stop all bots.")
    log("MAIN", "-" * 50)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("MAIN", "Shutting down all bots...")
        os._exit(0)


if __name__ == "__main__":
    main()
