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


def main():
    """Show launcher dialog and start the selected mode."""
    from miniclaude.ui.launcher import show_launcher, launch_cli
    from miniclaude.ui.desktop import launch_desktop

    choice = show_launcher()

    if choice == "cli":
        launch_cli()
    elif choice == "gui":
        launch_desktop()
    # "exit" = user closed the dialog, do nothing


if __name__ == "__main__":
    main()
