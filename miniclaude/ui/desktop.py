"""Tkinter Desktop GUI for MiniClaude — polished chat client."""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import messagebox
from typing import Any

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
#  Theme
# ══════════════════════════════════════════════════════════════════

class T:
    BG          = "#0b0b14"
    SURFACE     = "#14142a"
    ELEVATED    = "#1e1e3a"
    INPUT_BG    = "#161630"
    HOVER       = "#282850"

    FG          = "#e4e4f0"
    FG_DIM      = "#8888aa"
    FG_BRIGHT   = "#ffffff"

    ACCENT      = "#7c9aff"
    ACCENT_HOV  = "#99b0ff"
    ACCENT_DIM  = "#5570dd"

    USER_BG     = "#1a2e55"
    AI_BG       = "#181830"
    TOOL_BG_RUN = "#1c1c0a"
    TOOL_BG_OK  = "#0c1a14"
    TOOL_BG_ERR = "#1a0c14"

    GREEN       = "#5ee8a0"
    RED         = "#ff7090"
    YELLOW      = "#ffe088"
    ORANGE      = "#ffaa55"

    BORDER      = "#222244"
    BORDER_ACC  = "#3a55aa"

    # Dimmer border when input not focused
    INPUT_BORDER_NORMAL = "#2a2a50"
    INPUT_BORDER_FOCUS  = "#5580dd"


FONT      = ("Segoe UI", 11)
FONT_B    = ("Segoe UI", 11, "bold")
FONT_SM   = ("Segoe UI", 9)
FONT_SM_B = ("Segoe UI", 9, "bold")
FONT_TTL  = ("Segoe UI", 11, "bold")
FONT_MONO = ("Consolas", 10)
FONT_HERO = ("Segoe UI", 26, "bold")


# ══════════════════════════════════════════════════════════════════
#  DesktopApp
# ══════════════════════════════════════════════════════════════════

class DesktopApp:

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("MiniClaude")
        self.root.geometry("980x740")
        self.root.minsize(660, 500)
        self.root.configure(bg=T.BG)

        # State
        self._app: Any = None          # MiniClaudeApp (lazy)
        self._ready = False
        self._busy = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._placeholder = True
        self._thinking_id: str | None = None   # after-id for animation
        self._dots = 0

        # Build sections top-to-bottom
        self._build_toolbar()
        self._build_status_bar()       # pack(side="bottom") first
        self._build_input()            # pack(side="bottom") second
        self._build_chat()             # fill remaining

        # Shortcuts
        self.root.bind("<Control-n>", lambda e: self._new_session())
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Async background thread
        self._start_bg()
        self.root.after(150, self._focus_input)

    # ────────────────────────────── Toolbar ───────────────────────

    def _build_toolbar(self) -> None:
        bar = tk.Frame(self.root, bg=T.SURFACE, height=48)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        left = tk.Frame(bar, bg=T.SURFACE)
        left.pack(side="left", padx=16, pady=8)

        tk.Label(left, text="MiniClaude", font=FONT_TTL,
                 fg=T.ACCENT, bg=T.SURFACE).pack(side="left")

        right = tk.Frame(bar, bg=T.SURFACE)
        right.pack(side="right", padx=12, pady=8)

        self._btn(right, "  + New  ", self._new_session)
        self._btn(right, "  Clear  ", self._clear)

        tk.Label(right, text="  |  ", font=FONT_SM,
                 fg=T.BORDER, bg=T.SURFACE).pack(side="left")

        self._model_lbl = tk.Label(right, text="mimo-v2.5-pro",
                                   font=FONT_SM, fg=T.FG_DIM, bg=T.SURFACE)
        self._model_lbl.pack(side="left")

    def _btn(self, parent, text, cmd):
        b = tk.Label(parent, text=text, font=FONT_SM_B,
                     fg=T.FG_DIM, bg=T.ELEVATED, padx=8, pady=3, cursor="hand2")
        b.pack(side="left", padx=3)
        b.bind("<Button-1>", lambda e: cmd())
        b.bind("<Enter>", lambda e: b.configure(bg=T.HOVER, fg=T.FG))
        b.bind("<Leave>", lambda e: b.configure(bg=T.ELEVATED, fg=T.FG_DIM))

    # ────────────────────────────── Chat ──────────────────────────

    def _build_chat(self) -> None:
        wrap = tk.Frame(self.root, bg=T.BG)
        wrap.pack(fill="both", expand=True)

        self._chat = tk.Text(
            wrap, wrap="word", font=FONT, fg=T.FG, bg=T.BG,
            bd=0, padx=28, pady=20, spacing1=0, spacing3=0,
            state="disabled", cursor="arrow",
            selectbackground=T.ACCENT, selectforeground=T.FG_BRIGHT,
            highlightthickness=0, undo=False,
        )
        sb = tk.Scrollbar(wrap, command=self._chat.yview, bg=T.SURFACE,
                          troughcolor=T.BG, width=6,
                          activebackground=T.ELEVATED, highlightthickness=0, bd=0)
        self._chat.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._chat.pack(fill="both", expand=True)

        # ── Tag styles ────────────────────────────────────────────
        c = self._chat
        c.tag_configure("hero", font=FONT_HERO, foreground=T.ACCENT,
                        justify="center", spacing1=24, spacing3=6)
        c.tag_configure("sub", font=FONT, foreground=T.FG_DIM,
                        justify="center", spacing3=6)
        c.tag_configure("tips", font=FONT_SM, foreground=T.FG_DIM,
                        justify="center", spacing1=2, spacing3=2)
        c.tag_configure("sep", font=("Segoe UI", 1), foreground=T.BORDER,
                        lmargin1=40, rmargin=40, spacing1=10, spacing3=10)

        # User message
        c.tag_configure("u_name", font=FONT_SM_B, foreground=T.ACCENT,
                        lmargin1=0, spacing1=14)
        c.tag_configure("u_msg", font=FONT, foreground=T.FG_BRIGHT,
                        background=T.USER_BG, lmargin1=8, lmargin2=8,
                        rmargin=140, spacing1=8, spacing3=10)
        c.tag_configure("u_time", font=FONT_SM, foreground=T.FG_DIM,
                        lmargin1=8, spacing3=10)

        # AI message
        c.tag_configure("a_name", font=FONT_SM_B, foreground=T.GREEN,
                        lmargin1=0, spacing1=14)
        c.tag_configure("a_msg", font=FONT, foreground=T.FG,
                        background=T.AI_BG, lmargin1=8, lmargin2=8,
                        rmargin=8, spacing1=8, spacing3=10)
        c.tag_configure("a_time", font=FONT_SM, foreground=T.FG_DIM,
                        lmargin1=8, spacing3=10)

        # Tool calls
        c.tag_configure("t_run", font=FONT_MONO, foreground=T.ORANGE,
                        background=T.TOOL_BG_RUN,
                        lmargin1=32, lmargin2=32, spacing1=3, spacing3=3)
        c.tag_configure("t_ok", font=FONT_MONO, foreground=T.GREEN,
                        background=T.TOOL_BG_OK,
                        lmargin1=32, lmargin2=32, spacing1=3, spacing3=3)
        c.tag_configure("t_err", font=FONT_MONO, foreground=T.RED,
                        background=T.TOOL_BG_ERR,
                        lmargin1=32, lmargin2=32, spacing1=3, spacing3=3)
        c.tag_configure("t_pre", font=FONT_SM, foreground=T.FG_DIM,
                        lmargin1=48, lmargin2=48, spacing1=1, spacing3=1)

        # Thinking / status
        c.tag_configure("think", font=FONT_SM, foreground=T.FG_DIM,
                        lmargin1=8, spacing1=6, spacing3=6)
        c.tag_configure("sys", font=FONT_SM, foreground=T.FG_DIM,
                        justify="center", spacing1=8, spacing3=8)

        # Make chat area clickable to focus input
        self._chat.bind("<Button-1>", lambda e: self._focus_input())

    # ────────────────────────────── Input ─────────────────────────

    def _build_input(self) -> None:
        outer = tk.Frame(self.root, bg=T.BG)
        outer.pack(fill="x", side="bottom")

        # Divider
        tk.Frame(outer, bg=T.BORDER, height=1).pack(fill="x")

        row = tk.Frame(outer, bg=T.BG)
        row.pack(fill="x", padx=20, pady=14)

        # Wrapper — highlights on focus
        self._wrapper = tk.Frame(row, bg=T.INPUT_BORDER_NORMAL, bd=0)
        self._wrapper.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self._wrapper.bind("<Button-1>", lambda e: self._focus_input())

        inner = tk.Frame(self._wrapper, bg=T.INPUT_BG)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        self._input = tk.Text(
            inner, font=FONT, fg=T.FG, bg=T.INPUT_BG,
            bd=0, padx=12, pady=10, height=2, wrap="word",
            insertbackground=T.ACCENT, insertwidth=2,
            selectbackground=T.ACCENT, selectforeground=T.FG_BRIGHT,
            highlightthickness=0, undo=True,
        )
        self._input.pack(fill="both", expand=True)
        self._input.bind("<FocusIn>", self._on_focus_in)
        self._input.bind("<FocusOut>", self._on_focus_out)
        self._input.bind("<Return>", self._on_enter)
        self._input.bind("<Control-Return>", lambda e: self._on_send())

        # Right side: send button
        right_col = tk.Frame(row, bg=T.BG)
        right_col.pack(side="right")

        self._send_btn = tk.Label(
            right_col, text="  Send  ", font=FONT_B,
            fg=T.FG_BRIGHT, bg=T.ACCENT, padx=18, pady=18, cursor="hand2",
        )
        self._send_btn.pack()
        self._send_btn.bind("<Button-1>", lambda e: self._on_send())
        self._send_btn.bind("<Enter>",
                            lambda e: self._send_btn.configure(bg=T.ACCENT_HOV) if not self._busy else None)
        self._send_btn.bind("<Leave>",
                            lambda e: self._send_btn.configure(bg=T.ACCENT) if not self._busy else None)

        # Hint below input
        tk.Label(outer, text="Enter to send  |  Shift+Enter for newline  |  Ctrl+N new session",
                 font=FONT_SM, fg=T.FG_DIM, bg=T.BG).pack(pady=(0, 8))

        # Placeholder
        self._ph_text = "Ask me anything ..."
        self._show_ph()

    def _show_ph(self):
        self._input.delete("1.0", "end")
        self._input.insert("1.0", self._ph_text)
        self._input.configure(fg=T.FG_DIM)
        self._placeholder = True

    def _clear_ph(self):
        if self._placeholder:
            self._input.delete("1.0", "end")
            self._input.configure(fg=T.FG)
            self._placeholder = False

    def _on_focus_in(self, e):
        self._clear_ph()
        self._wrapper.configure(bg=T.INPUT_BORDER_FOCUS)

    def _on_focus_out(self, e):
        if not self._input.get("1.0", "end-1c").strip():
            self._show_ph()
        self._wrapper.configure(bg=T.INPUT_BORDER_NORMAL)

    def _on_enter(self, e):
        if e.state & 0x1:       # Shift held → newline
            return
        self._on_send()
        return "break"

    def _focus_input(self):
        self._input.focus_set()
        self._wrapper.configure(bg=T.INPUT_BORDER_FOCUS)

    # ────────────────────────────── Status Bar ────────────────────

    def _build_status_bar(self):
        bar = tk.Frame(self.root, bg=T.SURFACE, height=28)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self._status = tk.Label(bar, text="  Ready", font=FONT_SM,
                                fg=T.FG_DIM, bg=T.SURFACE, anchor="w")
        self._status.pack(fill="x", padx=10)

    def _set_status(self, text):
        self._status.configure(text=f"  {text}")

    # ────────────────────────────── Chat Helpers ──────────────────

    def _put(self, text, *tags):
        self._chat.configure(state="normal")
        tag = tags[0] if tags else ""
        self._chat.insert("end", text + "\n", tag)
        self._chat.configure(state="disabled")
        self._chat.see("end")

    def _put_raw(self, text, tag=""):
        """Insert without trailing newline."""
        self._chat.configure(state="normal")
        self._chat.insert("end", text, tag)
        self._chat.configure(state="disabled")
        self._chat.see("end")

    def _timestamp(self):
        return datetime.now().strftime("%H:%M")

    def _show_welcome(self):
        self._put("")
        self._put("MiniClaude", "hero")
        self._put("AI Coding Agent", "sub")
        self._put("")
        self._put("Tips:", "tips")
        self._put("  Enter = send   |   Shift+Enter = newline   |   Ctrl+N = new session", "tips")
        self._put("")

    def _show_user(self, text):
        self._put("", "sep")
        self._put("  You", "u_name")
        self._put(text, "u_msg")
        self._put(f"  {self._timestamp()}", "u_time")

    def _show_ai(self, text):
        self._put("")
        self._put("  MiniClaude", "a_name")
        self._put(text, "a_msg")
        self._put(f"  {self._timestamp()}", "a_time")

    def _show_tool_start(self, name, params):
        p = json.dumps(params, ensure_ascii=False)
        if len(p) > 80:
            p = p[:80] + " ..."
        self._put(f"    {name}({p})", "t_run")

    def _show_tool_end(self, name, ok, preview):
        icon = "OK" if ok else "ERR"
        tag = "t_ok" if ok else "t_err"
        self._put(f"    {icon}  {name}", tag)
        if preview:
            line = preview.split("\n")[0]
            if len(line) > 80:
                line = line[:80] + " ..."
            self._put(f"      {line}", "t_pre")

    def _show_error(self, msg):
        self._put(f"  Error: {msg}", "t_err")

    # ────────────────────────────── Thinking Animation ────────────

    def _start_thinking(self):
        self._dots = 0
        self._put("")
        self._put("  MiniClaude", "a_name")
        self._put_raw("  Thinking", "think")
        self._animate_dots()

    def _animate_dots(self):
        if not self._busy:
            return
        self._dots = (self._dots % 3) + 1
        dots = "." * self._dots + "   "  # pad to clear previous
        # Update the last line's dots
        self._chat.configure(state="normal")
        # Find the "Thinking" text and update dots after it
        # We'll just append/update via tag
        try:
            # Remove old dots tag content
            last = self._chat.index("end-2c linestart")
            # find "Thinking" position
            pos = self._chat.search("Thinking", "end-10l", stopindex="end")
            if pos:
                line_end = f"{pos} lineend"
                # Delete from after "Thinking" to end of that line
                think_end = f"{pos}+8c"
                self._chat.delete(think_end, line_end)
                self._chat.insert(think_end, dots, "think")
        except Exception:
            pass
        self._chat.configure(state="disabled")
        self._chat.see("end")
        self._thinking_id = self.root.after(400, self._animate_dots)

    def _stop_thinking(self):
        if self._thinking_id:
            self.root.after_cancel(self._thinking_id)
            self._thinking_id = None
        # Clean up the thinking line — remove dots
        self._chat.configure(state="normal")
        try:
            pos = self._chat.search("Thinking", "end-10l", stopindex="end")
            if pos:
                think_end = f"{pos}+8c"
                line_end = f"{pos} lineend"
                self._chat.delete(think_end, line_end)
        except Exception:
            pass
        self._chat.configure(state="disabled")

    # ────────────────────────────── Events ────────────────────────

    def _on_send(self):
        if self._busy:
            return
        text = self._input.get("1.0", "end-1c").strip()
        if not text or self._placeholder:
            return

        self._input.delete("1.0", "end")
        self._input.configure(fg=T.FG)
        self._placeholder = False

        self._show_user(text)

        self._busy = True
        self._send_btn.configure(text=" ... ", bg=T.FG_DIM, cursor="arrow")
        self._set_status("Thinking ...")
        self._start_thinking()
        self._run_async(text)

    def _on_close(self):
        if self._busy:
            if not messagebox.askokcancel("Quit", "Query is running. Quit?"):
                return
        if self._app and self._loop:
            asyncio.run_coroutine_threadsafe(self._app.shutdown(), self._loop)
        self.root.destroy()

    def _new_session(self):
        if self._app and self._app.context:
            self._app.context.clear()
        self._chat.configure(state="normal")
        self._chat.delete("1.0", "end")
        self._chat.configure(state="disabled")
        self._show_welcome()
        self._show_ph()
        self._set_status("New session started")
        self.root.after(50, self._focus_input)

    def _clear(self):
        self._chat.configure(state="normal")
        self._chat.delete("1.0", "end")
        self._chat.configure(state="disabled")

    # ────────────────────────────── Async ─────────────────────────

    def _start_bg(self):
        def _():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()
        threading.Thread(target=_, daemon=True).start()

    def _run_async(self, text):
        async def go():
            try:
                if not self._ready:
                    from miniclaude.app import MiniClaudeApp
                    self._app = MiniClaudeApp()
                    await self._app.initialize()
                    self._app.query_loop.set_callbacks(
                        on_tool_start=self._cb_tool,
                        on_tool_end=self._cb_tool_done,
                        on_thinking=self._cb_think,
                    )
                    self._ready = True
                    self.root.after(0, self._on_init)

                result = await self._app.run_query(text)
                self.root.after(0, self._on_done, result)
            except Exception as e:
                logger.error("Query failed: %s", e, exc_info=True)
                self.root.after(0, self._on_err, str(e))

        if self._loop:
            asyncio.run_coroutine_threadsafe(go(), self._loop)

    def _on_init(self):
        if self._app and self._app.config:
            self._model_lbl.configure(text=self._app.config.model)

    def _on_done(self, result):
        self._stop_thinking()
        self._busy = False
        self._send_btn.configure(text="  Send  ", bg=T.ACCENT, cursor="hand2")
        if self._app and self._app.query_loop:
            u = self._app.query_loop.token_usage
            self._set_status(
                f"Tokens {u.get('input_tokens',0):,} in + "
                f"{u.get('output_tokens',0):,} out   |   "
                f"iter {self._app.query_loop.iteration_count}   |   Ready"
            )
        self.root.after(50, self._focus_input)

    def _on_err(self, err):
        self._stop_thinking()
        self._busy = False
        self._send_btn.configure(text="  Send  ", bg=T.ACCENT, cursor="hand2")
        self._show_error(err)
        self._set_status(f"Error: {err[:60]}")
        self.root.after(50, self._focus_input)

    # ── Callbacks from async thread ──────────────────────────────

    def _cb_tool(self, name, params):
        self.root.after(0, self._show_tool_start, name, params)

    def _cb_tool_done(self, name, ok, preview):
        self.root.after(0, self._show_tool_end, name, ok, preview)

    def _cb_think(self, text):
        self.root.after(0, self._on_ai_text, text)

    def _on_ai_text(self, text):
        self._stop_thinking()
        self._show_ai(text)
        # Restart thinking animation if more iterations may follow
        if self._busy:
            self._start_thinking()

    # ────────────────────────────── Run ───────────────────────────

    def run(self):
        self._show_welcome()
        self._set_status("Ready   |   Enter: Send   |   Shift+Enter: Newline   |   Ctrl+N: New session")
        self.root.mainloop()


def launch_desktop() -> None:
    DesktopApp().run()
