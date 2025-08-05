import threading

import pytest
from flask import Flask, Response
from playwright._impl._errors import Error as PWError
from werkzeug.serving import make_server

from src.scrape.rss import _get_html


def test_browser_fallback():
    app = Flask(__name__)
    calls = {"count": 0}

    @app.route("/")
    def index():  # type: ignore[override]
        if calls["count"] == 0:
            calls["count"] += 1
            return Response("Forbidden", status=403)
        return (
            "<html><body><script>"
            "document.body.innerHTML='<div id=\"ok\">ok</div>'"
            "</script></body></html>"
        )

    server = make_server("127.0.0.1", 0, app)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        host, port = server.server_address
        try:
            body, status, _ = _get_html(f"http://{host}:{port}/")
        except PWError as exc:  # pragma: no cover - missing browser deps
            pytest.skip(f"Playwright unavailable: {exc}")
        assert status == 200
        assert b'id="ok"' in (body or b"")
    finally:
        server.shutdown()
        thread.join()
