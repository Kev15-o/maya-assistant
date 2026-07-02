"""
Tiny local JSON API exposing the shared assistant state.

server.py already does this (it serves both the page and /api/state from
the same Flask app). streamlit_app.py can't do that itself — Streamlit
owns its own server — so this module runs the same kind of endpoint on a
separate local port purely so the embedded templates/index.html page (an
iframe inside the Streamlit tab) can poll it with fetch(), exactly like it
already does when served by server.py.

CORS is enabled because the iframe (served by Streamlit, e.g. port 8501)
and this API (e.g. port 5051) are different origins as far as the browser
is concerned, even though both are on 127.0.0.1.
"""

from flask import Flask, jsonify

from state import state


def create_api_app():
    app = Flask(__name__)

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET"
        return response

    @app.route("/api/state")
    def api_state():
        return jsonify(state.snapshot())

    return app


def start_state_api(port=5051):
    """Blocking call — intended to be run on a background daemon thread."""
    app = create_api_app()
    # debug=False / use_reloader=False: this runs on a thread, not the main
    # process, and the reloader would try to spawn a second process.
    try:
        app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
    except OSError as exc:
        if "Address already in use" in str(exc):
            return
        raise
