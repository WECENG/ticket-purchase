# -*- coding: utf-8 -*-
"""
start.py - Cross-platform launcher for Damai ticket automation
Supports: Windows / macOS / Linux
Usage:   python start.py        (Mobile mode, Appium + Android)
         python start.py --web  (Web mode, Selenium + Chrome)
"""

import sys
import io
import os
import re
import time
import shutil
import subprocess
import argparse
import urllib.request
import urllib.error
from pathlib import Path

# Fix encoding on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")

PROJECT_DIR = Path(__file__).resolve().parent
APPIUM_PORT = 4723
APPIUM_URL = f"http://127.0.0.1:{APPIUM_PORT}"


# ---------------------------------------------------------------------------
# Platform helpers
# ---------------------------------------------------------------------------

def get_os_name():
    """Return human-readable OS name and package manager hint."""
    if sys.platform == "win32":
        return "Windows", "winget / choco"
    elif sys.platform == "darwin":
        return "macOS", "brew"
    else:
        return "Linux", "apt / yum"


def which(cmd):
    """Cross-platform 'which'."""
    return shutil.which(cmd)


def run_cmd(cmd, timeout=15, check=False):
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except Exception as e:
        return 1, "", str(e)


# ---------------------------------------------------------------------------
# Environment checks
# ---------------------------------------------------------------------------

def check_python():
    """Check Python >= 3.8"""
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 8):
        print(f"[FAIL] Python {major}.{minor} detected, need >= 3.8")
        print("  Install: https://www.python.org/downloads/")
        return False
    print(f"[OK] Python {major}.{minor}.{sys.version_info.micro}")
    return True


def check_node():
    """Check Node.js is available."""
    node = which("node")
    if not node:
        print("[FAIL] Node.js not found")
        os_name, _ = get_os_name()
        if os_name == "Windows":
            print("  Install: https://nodejs.org/ (download LTS 20.19+)")
        elif os_name == "macOS":
            print("  Install: brew install node")
        else:
            print("  Install: curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -")
            print("           sudo apt install -y nodejs")
        return False
    code, out, _ = run_cmd(["node", "--version"])
    if code == 0:
        print(f"[OK] Node.js {out.lstrip('v')}")
    return True


def check_npm():
    """Check npm is available."""
    npm = which("npm")
    if not npm:
        print("[FAIL] npm not found")
        return False
    print("[OK] npm available")
    return True


def check_appium():
    """Check Appium CLI is installed."""
    appium_bin = which("appium")
    if not appium_bin:
        print("[FAIL] Appium not installed")
        print("  Install: npm install -g appium")
        print("  Then:    appium driver install uiautomator2")
        return False
    code, out, _ = run_cmd([appium_bin, "--version"])
    if code == 0:
        print(f"[OK] Appium {out}")
    else:
        print(f"[WARN] appium --version failed, but binary found at {appium_bin}")
    return True


def check_uiautomator2():
    """Check UIAutomator2 driver is installed."""
    code, out, err = run_cmd([which("appium"), "driver", "list", "--installed"])
    if code != 0:
        print("[WARN] Cannot list Appium drivers, assuming OK")
        return True
    # appium driver list outputs to stderr on some platforms
    combined = (out + " " + err).lower()
    if "uiautomator2" not in combined:
        print("[FAIL] UIAutomator2 driver not installed")
        print("  Install: appium driver install uiautomator2")
        return False
    print("[OK] UIAutomator2 driver installed")
    return True


def check_adb():
    """Check ADB is available."""
    adb = which("adb")
    if not adb:
        print("[FAIL] adb not found")
        os_name, _ = get_os_name()
        if os_name == "Windows":
            print(f"  Install Android SDK Platform-Tools:")
            print(f"  https://developer.android.com/studio/releases/platform-tools")
            print(f"  or install Android Studio and add %LOCALAPPDATA%\\Android\\Sdk\\platform-tools to PATH")
        elif os_name == "macOS":
            print("  brew install android-platform-tools")
        else:
            print("  sudo apt install adb")
        return False
    code, out, _ = run_cmd(["adb", "version"])
    if code == 0:
        ver = out.split("\n")[0].strip()
        print(f"[OK] {ver}")
    return True


def check_device():
    """Check Android device is connected (warning only, not blocking)."""
    code, out, _ = run_cmd(["adb", "devices"])
    lines = [l for l in out.split("\n") if l.strip() and "device" in l]
    devices = [l for l in lines if not l.startswith("*") and not l.startswith("List")]
    if not devices:
        print("[WARN] No Android device detected")
        print("  Make sure:")
        print("  1. Phone is connected via USB")
        print("  2. Developer options + USB debugging enabled")
        print("  3. Confirm on phone when prompted")
        print("  Continuing anyway (Appium will fail if no device)...")
        return True
    for d in devices:
        print(f"[OK] Device: {d.split()[0]}")
    return True


def check_chrome():
    """Check Chrome is available."""
    paths = []
    if sys.platform == "win32":
        for base in [os.environ.get("PROGRAMFILES", r"C:\Program Files"),
                      os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
                      os.environ.get("LOCALAPPDATA", "")]:
            p = os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")
            if os.path.exists(p):
                paths.append(p)
    elif sys.platform == "darwin":
        mac_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if os.path.exists(mac_path):
            paths.append(mac_path)
    else:
        for p in ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
                   "/usr/bin/chromium", "/usr/bin/chromium-browser"]:
            if os.path.exists(p):
                paths.append(p)

    if not paths:
        print("[FAIL] Chrome browser not found")
        print("  Install: https://www.google.com/chrome/")
        return False
    print(f"[OK] Chrome: {paths[0]}")
    return True


# ---------------------------------------------------------------------------
# Appium server management
# ---------------------------------------------------------------------------

_appium_process = None


def start_appium():
    """Start Appium server in background."""
    global _appium_process
    appium_path = which("appium")
    if not appium_path:
        print("[FAIL] appium not found in PATH")
        return
    print(f"Starting Appium on port {APPIUM_PORT}...")
    _appium_process = subprocess.Popen(
        [appium_path, "--port", str(APPIUM_PORT), "--log-level", "error"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        encoding="utf-8",
        errors="replace",
    )
    time.sleep(1)


def wait_appium(max_wait=30):
    """Wait until Appium server responds."""
    status_url = f"{APPIUM_URL}/status"
    start = time.time()
    while time.time() - start < max_wait:
        try:
            req = urllib.request.Request(status_url)
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    elapsed = int(time.time() - start)
                    print(f"[OK] Appium ready ({elapsed}s)")
                    return True
        except Exception:
            pass
        elapsed = int(time.time() - start)
        print(f"  Waiting for Appium... ({elapsed}s/{max_wait}s)")
        time.sleep(2)
    print(f"[FAIL] Appium did not start within {max_wait}s")
    return False


def stop_appium():
    """Stop Appium server."""
    global _appium_process
    if _appium_process:
        print("Stopping Appium server...")
        _appium_process.terminate()
        try:
            _appium_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _appium_process.kill()
        _appium_process = None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def launch_web_console():
    """Launch the FastAPI Web Console on http://127.0.0.1:8765"""
    print("=" * 60)
    print("  Damai Ticket Automation - Web Console")
    print("=" * 60)
    print()
    print("Starting server on http://127.0.0.1:8765 ...")
    print("Open your browser to view the control panel.")
    print("Press Ctrl+C to stop.")
    print()
    
    # Check Python version (common requirement)
    if not check_python():
        sys.exit(1)
    
    # Run console server
    import subprocess
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    
    console_dir = PROJECT_DIR / "console"
    try:
        result = subprocess.run(
            [sys.executable, "-m", "console.server"],
            cwd=str(PROJECT_DIR),
            env=env,
            text=True, encoding="utf-8", errors="replace",
        )
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print()
        print("Server stopped.")

def main():
    parser = argparse.ArgumentParser(description="Damai ticket automation launcher")
    parser.add_argument("--cli", action="store_true",
                        help="Direct CLI mode (skip Web UI, run ticket grabbing immediately)")
    parser.add_argument("--web", action="store_true",
                        help="(CLI mode only) Use Web/Selenium mode instead of Mobile/Appium")
    args = parser.parse_args()

    # Default: launch Web console UI
    if not args.cli:
        launch_web_console()
        return

    # CLI mode: direct ticket grabbing
    mode = "Web" if args.web else "Mobile"
    os_name, pkg_mgr = get_os_name()

    print("=" * 60)
    print(f"  Damai Ticket Automation - {mode} Mode")
    print(f"  Platform: {os_name} ({pkg_mgr})")
    print("=" * 60)
    print()

    # Common checks
    print("--- Environment Check ---")
    all_ok = True
    all_ok &= check_python()

    if args.web:
        # Web mode checks
        all_ok &= check_chrome()
    else:
        # Mobile mode checks
        all_ok &= check_node()
        all_ok &= check_npm()
        all_ok &= check_appium()
        all_ok &= check_uiautomator2()
        all_ok &= check_adb()
        check_device()  # warning only, not blocking

    if not all_ok:
        print()
        print("=" * 60)
        print("[FAIL] Environment check failed. Fix issues above and retry.")
        print("=" * 60)
        sys.exit(1)

    print()
    print("[OK] All checks passed.")
    print()

    # Launch
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"

        if args.web:
            # Web mode: run damai/damai.py
            script = PROJECT_DIR / "damai" / "damai.py"
            print(f"Launching Web script: {script}")
            os.chdir(script.parent)
            result = subprocess.run([sys.executable, str(script)], env=env, stdin=sys.stdin, text=True, encoding="utf-8", errors="replace")
            sys.exit(result.returncode)
        else:
            # Mobile mode: start Appium, then run script
            start_appium()
            if not wait_appium():
                stop_appium()
                sys.exit(1)

            script = PROJECT_DIR / "damai_appium" / "damai_app_v2.py"
            print(f"Launching Mobile script: {script}")
            os.chdir(script.parent)
            result = subprocess.run([sys.executable, str(script)], env=env, stdin=sys.stdin, text=True, encoding="utf-8", errors="replace")
            stop_appium()
            sys.exit(result.returncode)
    except KeyboardInterrupt:
        print()
        print("Interrupted by user.")
    finally:
        if not args.web:
            stop_appium()

if __name__ == "__main__":
    main()
