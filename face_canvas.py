"""
FaceCanvas — a hand-drawn, animated sci-fi companion face on a plain
tkinter Canvas (CustomTkinter doesn't do custom vector drawing, so the
orb/eyes/mouth live on a raw Canvas dropped inside the CTk window).

Mirrors the look of the web version: a glowing orb, rotating dashed rings,
orbiting motes, soft round eyes that blink, expressive brows, and a mouth
that changes shape per state (line / smile / three dots / equalizer bars).
"""

import math
import random
import tkinter as tk

PALETTE = {
    "void": "#03050b",
    "panel": "#0b1526",
    "edge": "#173350",
    "core": "#39e9ff",
    "core_soft": "#8fe9ff",
    "violet": "#8b6bff",
    "violet_soft": "#b9a4ff",
    "deep": "#0d2842",
    "text_bright": "#ecf6ff",
    "text_dim": "#5d84ac",
    "text_faint": "#31496a",
    "standby_bar": "#1c3a58",
}

MODES = ("standby", "wake", "listening", "speaking")


class FaceCanvas(tk.Canvas):
    def __init__(self, master, palette=None, size=340, **kwargs):
        self.p = palette or PALETTE
        self.size = size
        self.c = size / 2
        super().__init__(master, width=size, height=size,
                          bg=self.p["void"], highlightthickness=0, **kwargs)

        self.mode = "standby"
        self.t = 0
        self._blinking = False
        self._blink_step = 0

        self._build_static()
        self._build_dynamic()
        self._schedule_blink()
        self.after(35, self._animate)

    # ---------------------------------------------------------------- build
    def _build_static(self):
        p, c, s = self.p, self.c, self.size
        pad, L = 8, 22

        # corner brackets
        for (x0, y0, dx, dy) in [
            (pad, pad, 1, 1), (s - pad, pad, -1, 1),
            (pad, s - pad, 1, -1), (s - pad, s - pad, -1, -1),
        ]:
            self.create_line(x0, y0 + dy * L, x0, y0, x0 + dx * L, y0,
                              fill=p["core_soft"], width=2)

        # rotating dashed rings (rotation faked via animated dashoffset)
        self.ring_a = self.create_oval(c - 168, c - 168, c + 168, c + 168,
                                        outline=p["edge"], width=1, dash=(2, 7))
        self.ring_b = self.create_oval(c - 154, c - 154, c + 154, c + 154,
                                        outline=p["violet_soft"], width=1, dash=(40, 8))
        self.ring_c = self.create_oval(c - 142, c - 142, c + 142, c + 142,
                                        outline=p["core_soft"], width=1.4, dash=(3, 10))

        # orbiting motes
        self.orbit_dots = [self.create_oval(0, 0, 6, 6, fill=p["core_soft"], outline="")
                            for _ in range(3)]

        # orb body
        self.orb_r = 128
        self.orb = self.create_oval(c - self.orb_r, c - self.orb_r,
                                     c + self.orb_r, c + self.orb_r,
                                     fill=p["deep"], outline=p["core_soft"], width=1.6)

        # cheeks (shown on wake/speaking)
        self.cheek_l = self.create_oval(c - 68, c + 6, c - 40, c + 24,
                                         fill=p["violet_soft"], outline="", state="hidden")
        self.cheek_r = self.create_oval(c + 40, c + 6, c + 68, c + 24,
                                         fill=p["violet_soft"], outline="", state="hidden")

        # scanline
        self.scanline = self.create_line(c - 90, c - self.orb_r + 10,
                                          c + 90, c - self.orb_r + 10,
                                          fill=p["core_soft"], width=2)

    def _build_dynamic(self):
        p, c = self.p, self.c
        self.eye_l_c = (c - 48, c - 12)
        self.eye_r_c = (c + 48, c - 12)
        self.eye_r_glow = 26
        self.eye_r_core = 15

        self.eye_l_glow = self.create_oval(0, 0, 0, 0, fill=p["core"], outline="", stipple="gray25")
        self.eye_r_glow = self.create_oval(0, 0, 0, 0, fill=p["core"], outline="", stipple="gray25")
        self.eye_l_core = self.create_oval(0, 0, 0, 0, fill=p["core"], outline="")
        self.eye_r_core = self.create_oval(0, 0, 0, 0, fill=p["core"], outline="")
        self.eye_l_spark = self.create_oval(0, 0, 0, 0, fill="#ffffff", outline="")
        self.eye_r_spark = self.create_oval(0, 0, 0, 0, fill="#ffffff", outline="")
        self._draw_eyes(1.0)

        # brows
        self.brow_l = self.create_line(c - 66, c - 46, c - 46, c - 58, c - 26, c - 48,
                                        fill=p["core_soft"], width=3, smooth=True,
                                        capstyle=tk.ROUND)
        self.brow_r = self.create_line(c + 26, c - 48, c + 46, c - 58, c + 66, c - 46,
                                        fill=p["core_soft"], width=3, smooth=True,
                                        capstyle=tk.ROUND)

        # ---- mouth variants (only one visible at a time) ----
        my = c + 44
        self.mouth_standby = self.create_line(c - 22, my, c + 22, my,
                                               fill=p["core_soft"], width=3, capstyle=tk.ROUND)
        self.mouth_wake = self.create_line(c - 26, my - 4, c, my + 16, c + 26, my - 4,
                                            fill=p["core_soft"], width=3, smooth=True,
                                            capstyle=tk.ROUND, state="hidden")
        self.mouth_dots = [
            self.create_oval(c - 24 + i * 12 - 3, my - 3, c - 24 + i * 12 + 3, my + 3,
                              fill=p["core_soft"], outline="", state="hidden")
            for i in range(3)
        ]
        n_bars, bw, gap = 6, 4, 5
        total = n_bars * bw + (n_bars - 1) * gap
        x0 = c - total / 2
        self.mouth_bars = []
        for i in range(n_bars):
            x = x0 + i * (bw + gap)
            bar = self.create_rectangle(x, my - 6, x + bw, my + 6,
                                         fill=p["violet_soft"], outline="", state="hidden")
            self.mouth_bars.append(bar)

        self.set_mode("standby")

    # -------------------------------------------------------------- drawing
    def _draw_eyes(self, squish):
        """squish = 1.0 normal, ~0.08 fully closed (blink)."""
        for (cx, cy), glow, core, spark in (
            (self.eye_l_c, self.eye_l_glow, self.eye_l_core, self.eye_l_spark),
            (self.eye_r_c, self.eye_r_glow, self.eye_r_core, self.eye_r_spark),
        ):
            rg, rc = self.eye_r_glow, self.eye_r_core
            hg, hc = rg * squish, rc * squish
            self.coords(glow, cx - rg, cy - hg, cx + rg, cy + hg)
            self.coords(core, cx - rc, cy - hc, cx + rc, cy + hc)
            sx, sy = cx - rc * 0.4, cy - hc * 0.4
            self.coords(spark, sx - 3, sy - 3, sx + 3, sy + 3)

    # -------------------------------------------------------------- public
    def set_mode(self, mode):
        if mode not in MODES or mode == self.mode:
            if mode in MODES:
                self.mode = mode
            return
        self.mode = mode
        p = self.p

        # mouth swap
        self.itemconfigure(self.mouth_standby, state="hidden")
        self.itemconfigure(self.mouth_wake, state="hidden")
        for d in self.mouth_dots:
            self.itemconfigure(d, state="hidden")
        for b in self.mouth_bars:
            self.itemconfigure(b, state="hidden")

        if mode == "standby":
            self.itemconfigure(self.mouth_standby, state="normal")
        elif mode == "wake":
            self.itemconfigure(self.mouth_wake, state="normal")
        elif mode == "listening":
            for d in self.mouth_dots:
                self.itemconfigure(d, state="normal")
        elif mode == "speaking":
            for b in self.mouth_bars:
                self.itemconfigure(b, state="normal")

        # cheeks
        show_cheeks = mode in ("wake", "speaking")
        self.itemconfigure(self.cheek_l, state="normal" if show_cheeks else "hidden")
        self.itemconfigure(self.cheek_r, state="normal" if show_cheeks else "hidden")

        # eye/core colour
        eye_color = p["violet_soft"] if mode == "speaking" else p["core"]
        self.itemconfigure(self.eye_l_core, fill=eye_color)
        self.itemconfigure(self.eye_r_core, fill=eye_color)

        # brow position per mode
        c = self.c
        offsets = {
            "standby": (3, 0.4),
            "wake": (-4, 0.9),
            "listening": (-2, 0.75),
            "speaking": (-1, 0.75),
        }
        dy, _alpha = offsets[mode]
        self.coords(self.brow_l, c - 66, c - 46 + dy, c - 46, c - 58 + dy, c - 26, c - 48 + dy)
        self.coords(self.brow_r, c + 26, c - 48 + dy, c + 46, c - 58 + dy, c + 66, c - 46 + dy)

    # -------------------------------------------------------------- blink
    def _schedule_blink(self):
        delay = int(random.uniform(2600, 5200))
        self.after(delay, self._start_blink)

    def _start_blink(self):
        self._blinking = True
        self._blink_step = 0
        self._schedule_blink()

    def _blink_tick(self):
        # 8-step triangular squish-and-release
        steps = 8
        self._blink_step += 1
        if self._blink_step > steps:
            self._blinking = False
            self._draw_eyes(1.0)
            return
        half = steps / 2
        d = self._blink_step
        frac = d / half if d <= half else (steps - d) / half
        squish = max(0.08, 1.0 - frac * 0.92)
        self._draw_eyes(squish)

    # -------------------------------------------------------------- loop
    def _animate(self):
        self.t += 1
        p, c = self.p, self.c

        # rotating dashed rings (marching dash offset ~= rotation)
        self.itemconfigure(self.ring_a, dashoffset=self.t % 200)
        self.itemconfigure(self.ring_b, dashoffset=-int(self.t * 1.4) % 200)
        self.itemconfigure(self.ring_c, dashoffset=int(self.t * 2.2) % 200)

        # orbiting motes
        speed = {"standby": 0.02, "wake": 0.035, "listening": 0.05, "speaking": 0.07}[self.mode]
        for i, dot in enumerate(self.orbit_dots):
            angle = self.t * speed + i * (2 * math.pi / len(self.orbit_dots))
            r = 150
            x = c + r * math.cos(angle)
            y = c + r * math.sin(angle)
            self.coords(dot, x - 3, y - 3, x + 3, y + 3)

        # breathing pulse of the orb
        pulse = math.sin(self.t * 0.05) * 1.5
        r = self.orb_r + pulse
        self.coords(self.orb, c - r, c - r, c + r, c + r)

        # scanline sweep
        top, bottom = c - self.orb_r + 10, c + self.orb_r - 10
        span = bottom - top
        speed_scan = {"standby": 1.4, "wake": 1.8, "listening": 2.4, "speaking": 3.2}[self.mode]
        y = top + ((self.t * speed_scan) % (span * 2))
        y = y if y <= bottom else (bottom * 2 - y)
        self.coords(self.scanline, c - 90, y, c + 90, y)

        # eyes: idle breathing / blink
        if self._blinking:
            self._blink_tick()
        else:
            idle = {"standby": 0.06, "wake": 0.03, "listening": 0.1, "speaking": 0.0}[self.mode]
            squish = 1.0 - abs(math.sin(self.t * 0.08)) * idle
            self._draw_eyes(squish)

        # mouth animation for listening dots / speaking bars
        if self.mode == "listening":
            for i, d in enumerate(self.mouth_dots):
                lift = abs(math.sin(self.t * 0.25 + i * 0.9)) * 4
                x0, y0, x1, y1 = self.coords(d)
                base_y = self.c + 44
                self.coords(d, x0, base_y - lift - 3, x1, base_y - lift + 3)
        elif self.mode == "speaking":
            my = self.c + 44
            for bar in self.mouth_bars:
                x0, _, x1, _ = self.coords(bar)
                h = random.uniform(6, 22)
                self.coords(bar, x0, my - h, x1, my + h)

        self.after(35, self._animate)
