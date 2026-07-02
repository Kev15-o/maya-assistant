"""
Thread-safe shared state.

The assistant loop (assistant.py) runs on a background thread and writes to
this object whenever something changes (mode, spoken text, weather, etc).
The Flask server (server.py) reads it on every request to /api/state.
"""

import threading
import time


class AssistantState:
    def __init__(self):
        self._lock = threading.Lock()
        self._state = {
            "mode": "standby",  # standby | wake | listening | speaking
            "sys_text": "SYSTEM STANDBY",
            "message": 'Standby. Say "wake up" to resume.',
            "weather_temp": None,
            "weather_cond": None,
            "last_query": "",
            "last_reply": "",
            "updated": time.time(),
        }

    def update(self, **kwargs):
        with self._lock:
            self._state.update(kwargs)
            self._state["updated"] = time.time()

    def snapshot(self):
        with self._lock:
            return dict(self._state)


# Single shared instance, imported by both assistant.py and server.py
state = AssistantState()
