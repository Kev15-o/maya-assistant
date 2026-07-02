"""
Desktop frontend for M.A.Y.A, built with CustomTkinter.

This is an alternative to server.py — it does not use Flask or a browser
at all. It starts the assistant loop on a background thread and reads the
shared `state` object directly (same process, no HTTP round-trip), polling
it a few times a second to update the face, panels, and transcript.

Run only ONE frontend at a time (this OR server.py) — both start
assistant.run_assistant(), and two copies would fight over the microphone.

    python desktop_app.py
"""

import math
import random
import threading
import time
import tkinter as tk

import customtkinter as ctk

import assistant
from state import state
from face_canvas import FaceCanvas, PALETTE

ctk.set_appearance_mode("dark")

MODE_LABEL_COLOR = {
    "standby": PALETTE["text_dim"],
    "wake": PALETTE["core_soft"],
    "listening": PALETTE["core_soft"],
    "speaking": PALETTE["violet_soft"],
}
MODE_DOT_COLOR = {
    "standby": PALETTE["text_faint"],
    "wake": PALETTE["core"],
    "listening": PALETTE["core_soft"],
    "speaking": PALETTE["violet_soft"],
}


class MayaApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("M.A.Y.A — Companion Display")
        self.geometry("720x820")
        self.minsize(640, 760)
        self.configure(fg_color=PALETTE["void"])

        self._last_query = ""
        self._build_ui()
        self._start_assistant()

        self.after(300, self._poll_state)
        self.after(60, self._animate_waveform)

    # ------------------------------------------------------------- backend
    def _start_assistant(self):
        t = threading.Thread(target=assistant.run_assistant, daemon=True)
        t.start()

    # ---------------------------------------------------------------- UI
    def _build_ui(self):
        p = PALETTE
        pad = 18

        # top bar
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=pad, pady=(pad, 8))

        brand_box = ctk.CTkFrame(top, fg_color="transparent")
        brand_box.pack(side="left", anchor="w")
        ctk.CTkLabel(brand_box, text="M · A · Y · A", font=("Segoe UI", 24, "bold"),
                     text_color=p["core_soft"]).pack(anchor="w")
        ctk.CTkLabel(brand_box, text="COMPANION DISPLAY  ·  LIVE-LINKED TO MAIN.PY",
                     font=("Segoe UI", 10), text_color=p["text_faint"]).pack(anchor="w")

        status_box = ctk.CTkFrame(top, fg_color="transparent")
        status_box.pack(side="right", anchor="e")
        self.status_dot = ctk.CTkLabel(status_box, text="●", font=("Segoe UI", 16),
                                        text_color=p["core"])
        self.status_dot.pack(side="left", padx=(0, 8))
        self.sys_text_label = ctk.CTkLabel(status_box, text="SYSTEM STANDBY",
                                            font=("Segoe UI", 12, "bold"),
                                            text_color=p["text_dim"])
        self.sys_text_label.pack(side="left")

        ctk.CTkFrame(self, height=1, fg_color=p["edge"]).pack(fill="x", padx=pad)

        # middle row: panels + stage
        mid = ctk.CTkFrame(self, fg_color="transparent")
        mid.pack(fill="both", expand=True, padx=pad, pady=16)
        mid.grid_columnconfigure(0, weight=0)
        mid.grid_columnconfigure(1, weight=1)
        mid.grid_columnconfigure(2, weight=0)

        clock_panel = self._make_panel(mid, "CHRONOMETER")
        clock_panel.grid(row=0, column=0, sticky="n", padx=(0, 12))
        self.clock_time_label = clock_panel.value_label
        self.clock_date_label = clock_panel.sub_label
        self.clock_time_label.configure(text="--:--:--")
        self.clock_date_label.configure(text="-- --- ----")

        stage_frame = ctk.CTkFrame(mid, fg_color="transparent")
        stage_frame.grid(row=0, column=1, sticky="n")
        self.face = FaceCanvas(stage_frame, palette=PALETTE, size=340)
        self.face.pack()

        weather_panel = self._make_panel(mid, "LOCAL SENSOR · KOCHI")
        weather_panel.grid(row=0, column=2, sticky="n", padx=(12, 0))
        self.weather_temp_label = weather_panel.value_label
        self.weather_cond_label = weather_panel.sub_label
        self.weather_temp_label.configure(text="--°")
        self.weather_cond_label.configure(text="Connecting…")

        ctk.CTkFrame(self, height=1, fg_color=p["edge"]).pack(fill="x", padx=pad, pady=(0, 12))

        # console
        console = ctk.CTkFrame(self, fg_color="transparent")
        console.pack(fill="x", padx=pad, pady=(0, pad))

        self.waveform = tk.Canvas(console, width=380, height=44, bg=p["void"],
                                   highlightthickness=0)
        self.waveform.pack(pady=(0, 12))
        self._build_waveform()

        self.state_text_label = ctk.CTkLabel(
            console, text='Standby. Say "wake up" to resume.',
            font=("Segoe UI", 14, "bold"), text_color=p["core_soft"])
        self.state_text_label.pack()

        self.transcript_label = ctk.CTkLabel(console, text="", font=("Segoe UI", 12),
                                              text_color=p["text_dim"], wraplength=620)
        self.transcript_label.pack(pady=(6, 0))

        ctk.CTkLabel(self, text="Linked to main.py — mirrors the running assistant in real time",
                     font=("Segoe UI", 9), text_color=p["text_faint"]).pack(pady=(0, 14))

    def _make_panel(self, master, label_text):
        p = PALETTE
        frame = ctk.CTkFrame(master, fg_color=p["panel"], border_color=p["edge"],
                              border_width=1, corner_radius=4, width=170)
        ctk.CTkLabel(frame, text=label_text, font=("Segoe UI", 9),
                     text_color=p["text_faint"]).pack(anchor="w", padx=14, pady=(14, 4))
        value_label = ctk.CTkLabel(frame, text="", font=("Consolas", 20, "bold"),
                                    text_color=p["text_bright"])
        value_label.pack(anchor="w", padx=14)
        sub_label = ctk.CTkLabel(frame, text="", font=("Segoe UI", 11),
                                  text_color=p["text_dim"])
        sub_label.pack(anchor="w", padx=14, pady=(2, 14))
        frame.value_label = value_label
        frame.sub_label = sub_label
        return frame

    def _build_waveform(self):
        p = PALETTE
        self.bars = []
        n, w, gap = 30, 4, 3
        total = n * (w + gap)
        x0 = (380 - total) // 2
        for i in range(n):
            x = x0 + i * (w + gap)
            bar = self.waveform.create_rectangle(x, 38 - 6, x + w, 38,
                                                  fill=p["standby_bar"], outline="")
            self.bars.append(bar)

    # ------------------------------------------------------------- loops
    def _animate_waveform(self):
        p = PALETTE
        mode = self.face.mode
        now = time.time()
        for i, bar in enumerate(self.bars):
            if mode == "standby":
                h, color = 4 + 4 * abs(math.sin(now * 1.4 + i * 0.3)), p["standby_bar"]
            elif mode == "wake":
                h, color = 4 + 6 * abs(math.sin(now * 2.2 + i * 0.3)), p["core"]
            elif mode == "listening":
                h, color = 6 + 20 * abs(math.sin(now * 3.4 + i * 0.4)), p["core_soft"]
            else:  # speaking
                h, color = 6 + 34 * random.random(), p["violet_soft"]
            x0, _, x1, _ = self.waveform.coords(bar)
            self.waveform.coords(bar, x0, 38 - h, x1, 38)
            self.waveform.itemconfigure(bar, fill=color)
        self.after(60, self._animate_waveform)

    def _poll_state(self):
        snap = state.snapshot()
        mode = snap.get("mode", "standby")
        self.face.set_mode(mode)

        self.status_dot.configure(text_color=MODE_DOT_COLOR.get(mode, PALETTE["core"]))
        self.sys_text_label.configure(text=snap.get("sys_text", ""),
                                       text_color=MODE_LABEL_COLOR.get(mode, PALETTE["text_dim"]))
        self.state_text_label.configure(text=snap.get("message", ""))

        wt, wc = snap.get("weather_temp"), snap.get("weather_cond")
        if wt:
            self.weather_temp_label.configure(text=wt)
        if wc:
            self.weather_cond_label.configure(text=wc)

        lq, lr = snap.get("last_query"), snap.get("last_reply")
        if lq:
            self._last_query = lq
        if self._last_query and lr:
            self.transcript_label.configure(
                text=f"You: {self._last_query}   →   Maya: {lr}")

        self.clock_time_label.configure(text=time.strftime("%I:%M:%S %p"))
        self.clock_date_label.configure(text=time.strftime("%a, %d %b %Y"))

        self.after(300, self._poll_state)


if __name__ == "__main__":
    app = MayaApp()
    app.mainloop()
