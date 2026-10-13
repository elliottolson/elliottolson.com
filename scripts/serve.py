#!/usr/bin/env python3
"""Preview the site locally.

Builds the site into dist/, drafts included, and serves it the way GitHub Pages
does, including showing 404.html for any path that doesn't exist. The site is rebuilt whenever
a file in site/ or content/ has changed, so a browser refresh shows the edit.

    python3 scripts/serve.py [port]
"""
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock

import build

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
built_at = 0.0
lock = Lock()


def newest_change():
    files = (path for folder in (build.SITE, build.CONTENT) for path in folder.rglob("*")
             if path.is_file() and not path.name.startswith("."))
    return max(path.stat().st_mtime for path in files)


def rebuild_if_changed():
    global built_at
    with lock:
        changed = newest_change()
        if changed <= built_at and build.DIST.exists():
            return
        built_at = changed
        try:
            build.main(drafts=True)
        except SystemExit as problem:
            print(f"Build failed: {problem}")


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # Pages trigger a rebuild check; the files a page then asks for do not
        if "." not in self.path.rsplit("/", 1)[-1].split("?")[0]:
            rebuild_if_changed()
        super().do_GET()

    def send_error(self, code, message=None, explain=None):
        page = build.DIST / "404.html"
        if code != 404 or not page.exists():
            return super().send_error(code, message, explain)
        body = page.read_bytes()
        self.send_response(404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    rebuild_if_changed()
    print(f"Serving the site at http://localhost:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), partial(Handler, directory=str(build.DIST))).serve_forever()
