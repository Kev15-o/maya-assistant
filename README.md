# M.A.Y.A — Voice Assistant + Live Companion Display

Your original `main.py` voice assistant, wired up to the sci-fi companion
face so the screen reflects what the assistant is actually doing.

There are **three interchangeable frontends** — pick one:

- `server.py` + `templates/index.html` — a browser face, served locally with Flask.
- `desktop_app.py` — a native desktop window built with CustomTkinter, no browser needed.
- `streamlit_app.py` — the same `index.html` face, running inside a Streamlit app instead of tkinter or a plain Flask page.

All three read the exact same `state.py` object and start the exact same
`assistant.py` loop, so run **only one at a time** — running more than one
would start multiple assistant threads fighting over your microphone.

## Project layout

```
maya_assistant/
├── server.py           # Flask frontend — run this OR desktop_app.py OR streamlit_app.py
├── desktop_app.py        # CustomTkinter frontend
├── face_canvas.py         # the animated face widget used by desktop_app.py
├── streamlit_app.py         # Streamlit frontend — embeds templates/index.html
├── state_api.py               # tiny local JSON API that streamlit_app.py's embedded page polls
├── assistant.py            # your assistant logic (adapted from main.py)
├── state.py                  # shared state every frontend reads/writes
├── templates/
│   └── index.html              # the browser face — served at http://127.0.0.1:5000
│                                # (also reused, embedded, by streamlit_app.py)
└── requirements.txt
```

## How it's wired together

- `state.py` holds one small thread-safe object: current mode
  (`standby` / `wake` / `listening` / `speaking`), the status text, the
  weather, and the last thing you said / Maya said back.
- `assistant.py` is your voice loop. It's unchanged in behavior — same
  wake word, same commands (weather, time, date, joke, wikipedia lookups,
  standby, exit) — but every time it calls `speak()`, listens for a
  command, or checks the weather, it now writes an update into that shared
  state.
- `server.py` starts the assistant loop on a background thread, and runs a
  tiny Flask server with one API route, `GET /api/state`, that returns the
  current state as JSON. It also serves the face itself.
- `templates/index.html` polls `/api/state` twice a second and updates the
  orb's expression, the status text, the weather panel, and a transcript
  line showing your last query and Maya's reply.

If the page can't reach the backend (e.g. you open the HTML file directly
without running `server.py`), it falls back to a **Preview** mode: the
manual Standby / Wake / Listening / Speaking buttons reappear so you can
still see the animations, and weather is fetched directly from wttr.in in
the browser instead.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
   `PyAudio` needs PortAudio on your system first:
   - macOS: `brew install portaudio`
   - Debian/Ubuntu: `sudo apt-get install portaudio19-dev`
   - Windows: usually installs fine via pip directly.

2. Run it:
   ```
   python server.py
   ```

3. Open **http://127.0.0.1:5000** in your browser. You should see the
   `LIVE` badge appear top-right within a second, and Maya will greet you
   with the time-of-day + weather, same as before — except now you can
   watch her listen, think, and speak.

### Or run the desktop version instead

Skip the browser entirely:

```
python desktop_app.py
```

This opens a native window with the same orb face, chronometer, weather
panel, waveform, and live transcript — driven directly off the shared
`state` object in the same process, no server or polling over HTTP
required. Close the window to quit.

### Or run the Streamlit version instead

```
streamlit run streamlit_app.py
```

This opens the same face you'd see from `templates/index.html`, but as a
Streamlit page instead of a browser tab pointed at Flask or a tkinter
window. Under the hood it starts the assistant loop on a background
thread (same as the other two frontends) plus a tiny local JSON API
(`state_api.py`, on port 5051 by default) that the embedded face polls
for live updates — the same request/response shape as `server.py`'s
`/api/state` route, just served on its own port since Streamlit owns its
own server process. Everything else — the orb, rings, eyes, mouth,
waveform, weather panel, chronometer — is pixel-for-pixel the same
`templates/index.html` markup, so it looks identical to the browser
version. Stop the Streamlit process to quit.

## Notes

- Only one browser tab needs to be open; the assistant itself is driven
  entirely by your microphone, not the browser. The page is a mirror, not
  a remote control — except in Preview mode, where the buttons are purely
  cosmetic for the animation.
- The assistant still prints everything to the terminal too (`maya: ...`,
  `User: ...`), exactly like before.
- To change the city for weather, edit the `wttr.in/Kochi` URL in
  `assistant.py` (`get_weather`) — and optionally the "Local Sensor ·
  Kochi" label in `templates/index.html`.
