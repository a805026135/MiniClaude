"""MiniClaude Launcher (debug version - shows console output)."""

import os
import sys
import io
import traceback
from pathlib import Path

# Fix Windows GBK encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

project_dir = Path(__file__).resolve().parent
os.chdir(project_dir)
sys.path.insert(0, str(project_dir))

try:
    from dotenv import load_dotenv
    load_dotenv(project_dir / ".env")
except ImportError:
    pass

os.environ["MINICLAUDE_PROJECT_DIR"] = str(project_dir)


def main():
    print("=" * 50)
    print("MiniClaude Launcher (Debug)")
    print("=" * 50)
    print(f"Python: {sys.executable}")
    print(f"Project: {project_dir}")
    print()

    try:
        from miniclaude.ui.launcher import show_launcher, launch_cli
        print("[OK] launcher imported")
    except Exception as e:
        print(f"[FAIL] import launcher: {e}")
        traceback.print_exc()
        input("Press Enter to exit...")
        return

    try:
        choice = show_launcher()
        print(f"[OK] user chose: {choice}")
    except Exception as e:
        print(f"[FAIL] launcher dialog: {e}")
        traceback.print_exc()
        input("Press Enter to exit...")
        return

    if choice == "cli":
        print("Launching CLI...")
        try:
            launch_cli()
            print("[OK] CLI launched")
        except Exception as e:
            print(f"[FAIL] CLI: {e}")
            traceback.print_exc()
            input("Press Enter to exit...")

    elif choice == "gui":
        print("Launching Desktop GUI...")
        try:
            from miniclaude.ui.desktop import DesktopApp
            print("[OK] desktop imported")
            app = DesktopApp()
            print("[OK] DesktopApp created, running...")
            app.run()
            print("[OK] Desktop exited")
        except Exception as e:
            print(f"[FAIL] Desktop: {e}")
            traceback.print_exc()
            input("Press Enter to exit...")

    else:
        print("Exited.")


if __name__ == "__main__":
    main()
