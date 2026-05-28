"""MiniClaude Launcher - Double-click to start.

Shows a mode selection dialog:
  - CLI Mode: Opens a new terminal window with the REPL
  - Desktop Mode: Opens the Tkinter GUI client

Usage:
  Double-click run.pyw on Windows (no console window)
  Or run: python run.pyw
"""

import os
import sys
import traceback
from pathlib import Path

# Ensure we're in the project directory
project_dir = Path(__file__).resolve().parent
os.chdir(project_dir)
sys.path.insert(0, str(project_dir))

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(project_dir / ".env")
except ImportError:
    pass

# Set project dir env var
os.environ["MINICLAUDE_PROJECT_DIR"] = str(project_dir)

# Log file for debugging .pyw (no console)
LOG_FILE = project_dir / "launcher_debug.log"


def log(msg: str) -> None:
    """Write to debug log."""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


def show_error(title: str, message: str) -> None:
    """Show an error dialog."""
    import tkinter as tk
    from tkinter import messagebox
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, message)
        root.destroy()
    except Exception:
        pass


def main():
    """Show launcher dialog and start the selected mode."""
    log("=== Launcher started ===")

    try:
        from miniclaude.ui.launcher import show_launcher, launch_cli
        log("launcher.py imported OK")
    except Exception as e:
        msg = f"Failed to import launcher:\n{traceback.format_exc()}"
        log(msg)
        show_error("MiniClaude - Import Error", msg)
        return

    try:
        choice = show_launcher()
        log(f"User chose: {choice}")
    except Exception as e:
        msg = f"Launcher dialog failed:\n{traceback.format_exc()}"
        log(msg)
        show_error("MiniClaude - Launcher Error", msg)
        return

    if choice == "cli":
        log("Launching CLI...")
        try:
            launch_cli()
            log("CLI launched OK")
        except Exception as e:
            msg = f"Failed to launch CLI:\n{traceback.format_exc()}"
            log(msg)
            show_error("MiniClaude - CLI Error", msg)

    elif choice == "gui":
        log("Launching Desktop GUI...")
        try:
            from miniclaude.ui.desktop import launch_desktop
            log("desktop.py imported OK")
            launch_desktop()
            log("Desktop exited normally")
        except Exception as e:
            msg = f"Desktop GUI failed:\n{traceback.format_exc()}"
            log(msg)
            show_error("MiniClaude - Desktop Error", msg)

    else:
        log("User exited")


if __name__ == "__main__":
    main()
