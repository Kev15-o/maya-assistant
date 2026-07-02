"""
Run this file to start both the voice assistant and the local web UI:

    python server.py

Then open http://127.0.0.1:5000 in a browser. The face on screen will track
the assistant's real state (standby / wake / listening / speaking) and show
weather, the last thing you said, and Maya's last reply.
"""

import threading

from flask import Flask, jsonify, render_template

import assistant
from state import state

app = Flask(__name__)

_assistant_thread = None
_assistant_lock = threading.Lock()


def start_assistant_once():
    """Starts the assistant loop on a daemon thread, exactly once."""
    global _assistant_thread
    with _assistant_lock:
        if _assistant_thread is None or not _assistant_thread.is_alive():
            _assistant_thread = threading.Thread(target=assistant.run_assistant, daemon=True)
            _assistant_thread.start()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/state")
def api_state():
    return jsonify(state.snapshot())


if __name__ == "__main__":
    start_assistant_once()
    # debug=False / use_reloader=False matters here: the reloader would spawn
    # a second process and a second assistant thread fighting over the mic.
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
