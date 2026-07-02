"""
Streamlit frontend for M.A.Y.A — replaces desktop_app.py (CustomTkinter).

Same shared architecture as the other frontends: it starts the assistant
loop once on a background thread and reads/writes nothing itself — all
state still lives in state.py.

The difference from desktop_app.py is *how* the face is drawn. tkinter's
Canvas has no notion of CSS/SVG, so face_canvas.py hand-draws and
hand-animates every ring, eye, and mouth shape with after()-based ticks.
Streamlit has no canvas API at all, but it *can* embed real HTML/CSS/SVG
via components.html — so instead of reimplementing the face a third time,
this file reuses the exact same markup as templates/index.html (the
browser version) inside an embedded iframe. That iframe's own JavaScript
polls a small local JSON API (state_api.py) for live state, exactly like
it already does when served by server.py — so the face's CSS animations
(breathing orb, spinning rings, blinking eyes, waveform bars) keep
running smoothly between polls instead of being redrawn from Python on
every refresh.

Run only ONE frontend at a time (server.py OR desktop_app.py OR this
one) — all three start assistant.run_assistant(), and more than one
running at once would fight over the microphone.

    streamlit run streamlit_app.py
"""

import threading
from pathlib import Path

import streamlit as st

import assistant
from state_api import start_state_api

API_PORT = 5051
PAGE_PATH = Path(__file__).parent / "templates" / "index.html"

st.set_page_config(page_title="M.A.Y.A — Companion Display", layout="wide")

# Strip Streamlit's default chrome/padding so the embedded face fills the
# tab edge-to-edge, matching what you'd see opening index.html directly.
st.markdown(
    """
    <style>
        #MainMenu, header, footer {visibility: hidden;}
        .block-container {padding: 0 !important; max-width: 100% !important;}
        iframe {border: none; display: block;}
    </style>
    """,
    unsafe_allow_html=True,
)

_backend_lock = threading.Lock()
_backend_started = False


def _ensure_backend_started():
    """Starts the assistant loop + local state API exactly once per process.

    This guards against both Streamlit reruns (script re-executes on every
    interaction) and multiple browser sessions hitting the same process —
    neither should spin up a second microphone thread or a second copy of
    the API server on an already-bound port.
    """
    global _backend_started
    with _backend_lock:
        if _backend_started:
            return
        threading.Thread(target=assistant.run_assistant, daemon=True).start()
        threading.Thread(
            target=start_state_api, kwargs={"port": API_PORT}, daemon=True
        ).start()
        _backend_started = True


def _load_page_html():
    html = PAGE_PATH.read_text(encoding="utf-8")
    # Tell the embedded page's own fetch() where to find the state API,
    # since it's running on a different port than the Streamlit page
    # itself (see the API_BASE fallback added in templates/index.html).
    injected = f"<script>window.MAYA_API_PORT = {API_PORT};</script>"
    return html.replace("<head>", "<head>\n" + injected, 1)


_ensure_backend_started()

if hasattr(st, "iframe"):
    # Streamlit >= 1.56: the current API.
    st.iframe(_load_page_html(), height=980)
else:
    # Older Streamlit: st.components.v1.html is deprecated but still works.
    import streamlit.components.v1 as components

    components.html(_load_page_html(), height=980, scrolling=False)