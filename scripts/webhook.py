"""Local notification inbox: only sanitised alert metadata is stored, never secrets."""
import json
import os
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timezone

STORE = Path(os.environ.get('NASLAB_INBOX', '/var/lib/naslab/notifications.jsonl'))


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/alerts':
            self.send_error(404)
            return
        length = int(self.headers.get('Content-Length', '0'))
        if length > 1048576:
            self.send_error(413)
            return
        try:
            body = json.loads(self.rfile.read(length))
            event = {'received_at': datetime.now(timezone.utc).isoformat(), 'payload': body}
            STORE.parent.mkdir(parents=True, exist_ok=True)
            with STORE.open('a') as f:
                f.write(json.dumps(event) + '\n')
        except (ValueError, OSError):
            self.send_error(400)
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'ok')

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        events = []
        if STORE.exists():
            for line in STORE.read_text().splitlines()[-150:]:
                try: events.append(json.loads(line))
                except ValueError: pass
        if self.path == '/api/events':
            self.wfile.write(json.dumps(events).encode())
        else:
            import html
            text = html.escape(json.dumps(events[::-1], indent=2, ensure_ascii=False))
            self.wfile.write(('<!doctype html><meta charset="utf-8"><title>NAS Lab Notification Inbox</title>'
                '<style>body{background:#101828;color:#d0d5dd;font:15px monospace;padding:32px}h1{color:#67e8f9}'
                'pre{white-space:pre-wrap}</style><h1>NAS Lab Notification Inbox</h1>'
                '<p>Alertmanager firing / resolved delivery evidence. Refresh to update.</p><pre>' + text + '</pre>').encode())


if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', 8088), Handler).serve_forever()
