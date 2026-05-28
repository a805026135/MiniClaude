"""Tkinter Desktop GUI for MiniClaude - polished chat-style client."""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import tkinter as tk
from tkinter import messagebox
from typing import Any

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
#  Theme — High-contrast dark palette
# ══════════════════════════════════════════════════════════════════

class Theme:
    # Backgrounds
    BG          = "#0f0f17"      # Main window background
    SURFACE     = "#1a1a28"      # Panels, toolbar
    ELEVATED    = "#242438"      # Cards, bubbles
    INPUT_BG    = "#1e1e30"      # Input field background
    HOVER       = "#2d2d48"      # Hover states

    # Foregrounds
    FG          = "#e8e8f0"      # Primary text — high contrast
    FG_DIM      = "#9898b0"      # Secondary text
    FG_BRIGHT   = "#ffffff"      # Bright text emphasis

    # Accents
    ACCENT      = "#6c8cff"      # Buttons, links, highlights
    ACCENT_DIM  = "#4a66cc"      # Accent hover
    USER_BUBBLE = "#1e3a5f"      # User message bubble
    AI_BUBBLE   = "#1f1f33"      # AI message bubble

    # Status colors
    GREEN       = "#50d890"      # Success
    RED         = "#ff6b8a"      # Error
    YELLOW      = "#ffd866"      # Warning / tool calls
    ORANGE      = "#ff9f43"      # Running

    # Borders
    BORDER      = "#2a2a42"      # Subtle borders
    BORDER_ACCENT = "#3d5a99"    # Accent borders


# ══════════════════════════════════════════════════════════════════
#  Fonts
# ══════════════════════════════════════════════════════════════════

FONT         = ("Segoe UI", 11)
FONT_BOLD    = ("Segoe UI", 11, "bold")
FONT_SMALL   = ("Segoe UI", 9)
FONT_TITLE   = ("Segoe UI", 10, "bold")
FONT_CODE    = ("Consolas", 10)
FONT_HERO    = ("Segoe UI", 24, "bold")


# ══════════════════════════════════════════════════════════════════
#  DesktopApp
# ══════════════════════════════════════════════════════════════════

class DesktopApp:
    """Polished Tkinter desktop client for MiniClaude."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("MiniClaude")
        self.root.geometry("960x720")
        self.root.minsize(640, 480)
        self.root.configure(bg=Theme.BG)

        # State
        self._mini_app: Any = None
        self._initialized = False
        self._is_running = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._input_placeholder = True

        # Build
        self._build_toolbar()
        self._build_chat_area()
        self._build_input_area()
        self._build_status_bar()

        # Shortcuts
        self.root.bind("<Control-Return>", lambda e: self._on_send())
        self.root.bind("<Control-n>", lambda e: self._new_session())

        self._start_async_thread()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ──────────────────────────────────────────────────────────────
    #  Toolbar
    # ──────────────────────────────────────────────────────────────

    def _build_toolbar(self) -> None:
        bar = tk.Frame(self.root, bg=Theme.SURFACE, height=50)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        # Left: logo + title
        left = tk.Frame(bar, bg=Theme.SURFACE)
        left.pack(side="left", padx=16)

        tk.Label(left, text="MiniClaude", font=FONT_TITLE,
                 fg=Theme.ACCENT, bg=Theme.SURFACE).pack(side="left")
        tk.Label(left, text="  v0.1.0", font=FONT_SMALL,
                 fg=Theme.FG_DIM, bg=Theme.SURFACE).pack(side="left", pady=(2, 0))

        # Right: action buttons
        right = tk.Frame(bar, bg=Theme.SURFACE)
        right.pack(side="right", padx=12)

        self._toolbar_btn(right, "New", self._new_session)
        self._toolbar_btn(right, "Clear", self._clear_chat)

        self._model_lbl = tk.Label(right, text="mimo-v2.5-pro", font=FONT_SMALL,
                                   fg=Theme.FG_DIM, bg=Theme.SURFACE)
        self._model_lbl.pack(side="right", padx=(12, 0))

    def _toolbar_btn(self, parent: tk.Frame, text: str, cmd: Any) -> tk.Button:
        btn = tk.Label(parent, text=text, font=FONT_SMALL,
                       fg=Theme.FG_DIM, bg=Theme.ELEVATED,
                       padx=12, pady=4, cursor="hand2")
        btn.pack(side="left", padx=4)
        btn.bind("<Button-1>", lambda e: cmd())
        btn.bind("<Enter>", lambda e: btn.configure(bg=Theme.HOVER, fg=Theme.FG))
        btn.bind("<Leave>", lambda e: btn.configure(bg=Theme.ELEVATED, fg=Theme.FG_DIM))
        return btn

    # ──────────────────────────────────────────────────────────────
    #  Chat Area
    # ──────────────────────────────────────────────────────────────

    def _build_chat_area(self) -> None:
        wrap = tk.Frame(self.root, bg=Theme.BG)
        wrap.pack(fill="both", expand=True, padx=0, pady=0)

        self._chat = tk.Text(
            wrap, wrap="word", font=FONT, fg=Theme.FG, bg=Theme.BG,
            bd=0, padx=24, pady=16, spacing1=2, spacing3=6,
            state="disabled", cursor="arrow",
            selectbackground=Theme.ACCENT, selectforeground=Theme.FG_BRIGHT,
            highlightthickness=0,
        )
        sb = tk.Scrollbar(wrap, command=self._chat.yview, bg=Theme.SURFACE,
                          troughcolor=Theme.BG, width=8,
                          activebackground=Theme.ELEVATED,
                          highlightthickness=0, bd=0)
        self._chat.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y", padx=(0, 2))
        self._chat.pack(fill="both", expand=True)

        # ── Tags ──────────────────────────────────────────────────
        # Role labels
        self._chat.tag_configure("user_label",
                                 font=FONT_BOLD, foreground=Theme.ACCENT,
                                 lmargin1=24, spacing1=12)
        self._chat.tag_configure("ai_label",
                                 font=FONT_BOLD, foreground=Theme.GREEN,
                                 lmargin1=24, spacing1=12)

        # Message bubbles
        self._chat.tag_configure("user_msg",
                                 font=FONT, foreground=Theme.FG_BRIGHT,
                                 background=Theme.USER_BUBBLE,
                                 lmargin1=24, lmargin2=24, rmargin=120,
                                 spacing1=6, spacing3=8)
        self._chat.tag_configure("ai_msg",
                                 font=FONT, foreground=Theme.FG,
                                 background=Theme.AI_BUBBLE,
                                 lmargin1=24, lmargin2=24, rmargin=24,
                                 spacing1=6, spacing3=8)

        # Tool call line
        self._chat.tag_configure("tool_running",
                                 font=FONT_CODE, foreground=Theme.ORANGE,
                                 lmargin1=40, lmargin2=40,
                                 background="#1a1a10",
                                 spacing1=3, spacing3=3)
        self._chat.tag_configure("tool_ok",
                                 font=FONT_CODE, foreground=Theme.GREEN,
                                 lmargin1=40, lmargin2=40,
                                 background="#0f1a14",
                                 spacing1=3, spacing3=3)
        self._chat.tag_configure("tool_err",
                                 font=FONT_CODE, foreground=Theme.RED,
                                 lmargin1=40, lmargin2=40,
                                 background="#1a0f14",
                                 spacing1=3, spacing3=3)
        self._chat.tag_configure("tool_preview",
                                 font=FONT_SMALL, foreground=Theme.FG_DIM,
                                 lmargin1=56, lmargin2=56)

        # System
        self._chat.tag_configure("system",
                                 font=FONT_SMALL, foreground=Theme.FG_DIM,
                                 justify="center", spacing1=8, spacing3=8)
        self._chat.tag_configure("divider",
                                 font=("Segoe UI", 1), foreground=Theme.BORDER,
                                 lmargin1=40, rmargin=40, spacing1=6, spacing3=6)
        self._chat.tag_configure("welcome_hero",
                                 font=FONT_HERO, foreground=Theme.ACCENT,
                                 justify="center", spacing1=20, spacing3=4)
        self._chat.tag_configure("welcome_sub",
                                 font=FONT, foreground=Theme.FG_DIM,
                                 justify="center", spacing3=20)

    # ──────────────────────────────────────────────────────────────
    #  Input Area
    # ──────────────────────────────────────────────────────────────

    def _build_input_area(self) -> None:
        outer = tk.Frame(self.root, bg=Theme.BG)
        outer.pack(fill="x", side="bottom", padx=16, pady=(0, 0))

        # Separator line
        tk.Frame(outer, bg=Theme.BORDER, height=1).pack(fill="x", pady=(0, 12))

        row = tk.Frame(outer, bg=Theme.BG)
        row.pack(fill="x")

        # Input field wrapper
        wrapper = tk.Frame(row, bg=Theme.BORDER_ACCENT, bd=0,
                           highlightthickness=1, highlightbackground=Theme.BORDER,
                           highlightcolor=Theme.ACCENT)
        wrapper.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self._input = tk.Text(
            wrapper, font=FONT, fg=Theme.FG, bg=Theme.INPUT_BG,
            bd=0, padx=14, pady=12, height=2, wrap="word",
            insertbackground=Theme.ACCENT, insertwidth=2,
            selectbackground=Theme.ACCENT, selectforeground=Theme.FG_BRIGHT,
            highlightthickness=0,
        )
        self._input.pack(fill="both", expand=True, padx=2, pady=2)

        # Placeholder
        self._placeholder_text = "Type a message ...   Ctrl+Enter to send"
        self._show_placeholder()
        self._input.bind("<FocusIn>", self._on_focus_in)
        self._input.bind("<FocusOut>", self._on_focus_out)
        self._input.bind("<Control-Return>", lambda e: self._on_send())
        # Also support plain Enter to send (Shift+Enter for newline)
        self._input.bind("<Return>", self._on_enter)

        # Send button
        self._send_btn = tk.Label(
            row, text="  Send  ", font=FONT_BOLD,
            fg=Theme.FG_BRIGHT, bg=Theme.ACCENT,
            padx=18, pady=12, cursor="hand2",
        )
        self._send_btn.pack(side="right")
        self._send_btn.bind("<Button-1>", lambda e: self._on_send())
        self._send_btn.bind("<Enter>",
                            lambda e: self._send_btn.configure(bg=Theme.ACCENT_DIM))
        self._send_btn.bind("<Leave>",
                            lambda e: self._send_btn.configure(bg=Theme.ACCENT))

        # Bottom padding
        tk.Frame(outer, bg=Theme.BG, height=12).pack()

    def _show_placeholder(self) -> None:
        self._input.delete("1.0", "end")
        self._input.insert("1.0", self._placeholder_text)
        self._input.configure(fg=Theme.FG_DIM)
        self._input_placeholder = True

    def _clear_placeholder(self) -> None:
        if self._input_placeholder:
            self._input.delete("1.0", "end")
            self._input.configure(fg=Theme.FG)
            self._input_placeholder = False

    def _on_focus_in(self, event: tk.Event) -> None:
        self._clear_placeholder()

    def _on_focus_out(self, event: tk.Event) -> None:
        if not self._input.get("1.0", "end-1c").strip():
            self._show_placeholder()

    def _on_enter(self, event: tk.Event) -> None:
        """Plain Enter sends; Shift+Enter inserts newline."""
        if event.state & 0x1:  # Shift held
            return  # Allow newline
        self._on_send()
        return "break"  # Prevent default newline

    # ──────────────────────────────────────────────────────────────
    #  Status Bar
    # ──────────────────────────────────────────────────────────────

    def _build_status_bar(self) -> None:
        bar = tk.Frame(self.root, bg=Theme.SURFACE, height=30)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self._status = tk.Label(
            bar, text="  Ready", font=FONT_SMALL,
            fg=Theme.FG_DIM, bg=Theme.SURFACE, anchor="w",
        )
        self._status.pack(fill="x", padx=8)

    def _set_status(self, text: str) -> None:
        self._status.configure(text=f"  {text}")

    # ──────────────────────────────────────────────────────────────
    #  Chat Display Helpers
    # ──────────────────────────────────────────────────────────────

    def _append(self, text: str, tag: str = "", newline: str = "\n") -> None:
        self._chat.configure(state="normal")
        self._chat.insert("end", text + newline, tag if tag else ())
        self._chat.configure(state="disabled")
        self._chat.see("end")

    def _show_welcome(self) -> None:
        self._append("")
        self._append("MiniClaude", "welcome_hero")
        self._append("AI Coding Agent  powered by MiMo-v2.5-pro", "welcome_sub")
        self._append("Type a message below to get started.", "system")
        self._append("")

    def _show_user_msg(self, text: str) -> None:
        self._append("")
        self._append("  You", "user_label")
        self._append(text, "user_msg")

    def _show_ai_msg(self, text: str) -> None:
        self._append("")
        self._append("  MiniClaude", "ai_label")
        self._append(text, "ai_msg")

    def _show_tool_running(self, name: str, params: dict) -> None:
        p = json.dumps(params, ensure_ascii=False)
        if len(p) > 80:
            p = p[:80] + " ..."
        self._append(f"   {name}({p})", "tool_running")

    def _show_tool_done(self, name: str, ok: bool, preview: str) -> None:
        icon = "OK" if ok else "ERR"
        tag = "tool_ok" if ok else "tool_err"
        self._append(f"   {icon}  {name}", tag)
        if preview:
            line = preview.split("\n")[0]
            if len(line) > 90:
                line = line[:90] + " ..."
            self._append(f"      {line}", "tool_preview")

    def _show_error(self, msg: str) -> None:
        self._append(f"  Error: {msg}", "tool_err")

    def _show_system(self, text: str) -> None:
        self._append(text, "system")

    # ──────────────────────────────────────────────────────────────
    #  Event Handlers
    # ──────────────────────────────────────────────────────────────

    def _on_send(self) -> None:
        if self._is_running:
            return
        text = self._input.get("1.0", "end-1c").strip()
        if not text or self._input_placeholder:
            return

        self._input.delete("1.0", "end")
        self._input.configure(fg=Theme.FG)
        self._input_placeholder = False

        self._show_user_msg(text)

        self._is_running = True
        self._send_btn.configure(text=" ... ", bg=Theme.FG_DIM, cursor="arrow")
        self._set_status("Thinking ...")
        self._run_async(text)

    def _on_close(self) -> None:
        if self._is_running:
            if not messagebox.askokcancel("Quit", "Query is running. Quit?"):
                return
        if self._mini_app and self._loop:
            asyncio.run_coroutine_threadsafe(self._mini_app.shutdown(), self._loop)
        self.root.destroy()

    def _new_session(self) -> None:
        if self._mini_app and self._mini_app.context:
            self._mini_app.context.clear()
        self._chat.configure(state="normal")
        self._chat.delete("1.0", "end")
        self._chat.configure(state="disabled")
        self._show_welcome()
        self._set_status("New session started")

    def _clear_chat(self) -> None:
        self._chat.configure(state="normal")
        self._chat.delete("1.0", "end")
        self._chat.configure(state="disabled")

    # ──────────────────────────────────────────────────────────────
    #  Async Integration
    # ──────────────────────────────────────────────────────────────

    def _start_async_thread(self) -> None:
        def loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()
        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def _run_async(self, user_input: str) -> None:
        async def go():
            try:
                if not self._initialized:
                    from miniclaude.app import MiniClaudeApp
                    self._mini_app = MiniClaudeApp()
                    await self._mini_app.initialize()
                    self._mini_app.query_loop.set_callbacks(
                        on_tool_start=self._cb_tool_start,
                        on_tool_end=self._cb_tool_end,
                        on_thinking=self._cb_thinking,
                    )
                    self._initialized = True
                    self.root.after(0, self._on_ready)

                result = await self._mini_app.run_query(user_input)
                self.root.after(0, self._on_done, result)
            except Exception as e:
                logger.error("Query failed: %s", e, exc_info=True)
                self.root.after(0, self._on_error, str(e))

        if self._loop:
            asyncio.run_coroutine_threadsafe(go(), self._loop)

    def _on_ready(self) -> None:
        if self._mini_app and self._mini_app.config:
            self._model_lbl.configure(text=self._mini_app.config.model)

    def _on_done(self, result: str) -> None:
        self._is_running = False
        self._send_btn.configure(text="  Send  ", bg=Theme.ACCENT, cursor="hand2")
        if self._mini_app and self._mini_app.query_loop:
            u = self._mini_app.query_loop.token_usage
            self._set_status(
                f"Tokens {u.get('input_tokens',0):,} in + {u.get('output_tokens',0):,} out  |  "
                f"iter {self._mini_app.query_loop.iteration_count}  |  Ready"
            )

    def _on_error(self, err: str) -> None:
        self._is_running = False
        self._send_btn.configure(text="  Send  ", bg=Theme.ACCENT, cursor="hand2")
        self._show_error(err)
        self._set_status(f"Error: {err[:60]}")

    # ── Callbacks (from async thread → main thread) ───────────

    def _cb_tool_start(self, name: str, params: dict) -> None:
        self.root.after(0, self._show_tool_running, name, params)

    def _cb_tool_end(self, name: str, ok: bool, preview: str) -> None:
        self.root.after(0, self._show_tool_done, name, ok, preview)

    def _cb_thinking(self, text: str) -> None:
        self.root.after(0, self._show_ai_msg, text)

    # ──────────────────────────────────────────────────────────────
    #  Run
    # ──────────────────────────────────────────────────────────────

    def run(self) -> None:
        self._show_welcome()
        self._set_status("Ready  |  Ctrl+N: New session  |  Enter: Send  |  Shift+Enter: Newline")
        self.root.mainloop()


def launch_desktop() -> None:
    """Entry point for the desktop GUI."""
    app = DesktopApp()
    app.run()
