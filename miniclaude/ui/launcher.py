"""Mode selection launcher dialog for MiniClaude."""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path


# ── Shared Theme ────────────────────────────────────────────────
BG       = "#0f0f17"
FG       = "#e8e8f0"
FG_DIM   = "#9898b0"
SURFACE  = "#1a1a28"
ELEVATED = "#242438"
HOVER    = "#2d2d48"
ACCENT   = "#6c8cff"
GREEN    = "#50d890"
BORDER   = "#2a2a42"


def show_launcher() -> str:
    """Show the mode selection dialog.  Returns 'cli', 'gui', or 'exit'."""
    result = {"choice": "exit"}

    root = tk.Tk()
    root.title("MiniClaude")
    root.geometry("500x420")
    root.resizable(False, False)
    root.configure(bg=BG)
    root.attributes("-topmost", True)
    root.overrideredirect(False)

    # Center
    root.update_idletasks()
    x = (root.winfo_screenwidth() - 500) // 2
    y = (root.winfo_screenheight() - 420) // 2
    root.geometry(f"500x420+{x}+{y}")

    def on_choose(mode: str) -> None:
        result["choice"] = mode
        root.destroy()

    # ── Title ────────────────────────────────────────────────────
    tk.Label(root, text="MiniClaude", font=("Segoe UI", 30, "bold"),
             fg=ACCENT, bg=BG).pack(pady=(36, 0))
    tk.Label(root, text="AI Coding Agent  v0.1.0", font=("Segoe UI", 10),
             fg=FG_DIM, bg=BG).pack(pady=(4, 0))

    # ── Separator ────────────────────────────────────────────────
    tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=40, pady=22)

    tk.Label(root, text="Choose a mode", font=("Segoe UI", 11),
             fg=FG, bg=BG).pack(pady=(0, 18))

    # ── Mode Cards ───────────────────────────────────────────────
    cards = tk.Frame(root, bg=BG)
    cards.pack()

    def make_card(parent, icon, title, desc, mode):
        card = tk.Frame(parent, bg=ELEVATED, cursor="hand2",
                        padx=28, pady=20, highlightthickness=1,
                        highlightbackground=BORDER, highlightcolor=ACCENT)
        card.pack(side="left", padx=10)

        tk.Label(card, text=icon, font=("Segoe UI", 28),
                 fg=ACCENT, bg=ELEVATED).pack()
        tk.Label(card, text=title, font=("Segoe UI", 13, "bold"),
                 fg=FG, bg=ELEVATED).pack(pady=(8, 3))
        tk.Label(card, text=desc, font=("Segoe UI", 9),
                 fg=FG_DIM, bg=ELEVATED).pack()

        def enter(e):
            card.configure(bg=HOVER)
            for w in card.winfo_children():
                w.configure(bg=HOVER)
        def leave(e):
            card.configure(bg=ELEVATED)
            for w in card.winfo_children():
                w.configure(bg=ELEVATED)

        for w in [card] + list(card.winfo_children()):
            w.bind("<Button-1>", lambda e: on_choose(mode))
            w.bind("<Enter>", enter)
            w.bind("<Leave>", leave)

    make_card(cards, ">_",  "CLI",     "Terminal REPL",   "cli")
    make_card(cards, "[]",  "Desktop", "GUI client",      "gui")

    # ── Project dir ──────────────────────────────────────────────
    proj = os.environ.get("MINICLAUDE_PROJECT_DIR", str(Path.cwd()))
    tk.Label(root, text=f"Project: {proj}", font=("Segoe UI", 9),
             fg=FG_DIM, bg=BG).pack(pady=(24, 0))

    # ── Exit ─────────────────────────────────────────────────────
    exit_lbl = tk.Label(root, text="Exit", font=("Segoe UI", 9),
                        fg=FG_DIM, bg=BG, cursor="hand2", padx=8, pady=4)
    exit_lbl.pack(pady=(12, 0))
    exit_lbl.bind("<Button-1>", lambda e: root.destroy())
    exit_lbl.bind("<Enter>", lambda e: exit_lbl.configure(fg=FG))
    exit_lbl.bind("<Leave>", lambda e: exit_lbl.configure(fg=FG_DIM))

    # Keys
    root.bind("<Escape>", lambda e: root.destroy())
    root.bind("1", lambda e: on_choose("cli"))
    root.bind("2", lambda e: on_choose("gui"))

    root.mainloop()
    return result["choice"]


def launch_cli() -> None:
    """Launch CLI mode in a new console window."""
    project_dir = Path(__file__).resolve().parent.parent.parent

    if sys.platform == "win32":
        subprocess.Popen(
            ["cmd", "/k", "cd", "/d", str(project_dir),
             "&&", "python", "-m", "miniclaude"],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            cwd=str(project_dir),
        )
    else:
        for terminal in ["gnome-terminal", "konsole", "xterm"]:
            try:
                subprocess.Popen(
                    [terminal, "-e",
                     f"bash -c 'cd {project_dir} && python -m miniclaude; exec bash'"],
                )
                break
            except FileNotFoundError:
                continue
        else:
            subprocess.run([sys.executable, "-m", "miniclaude"],
                           cwd=str(project_dir))
