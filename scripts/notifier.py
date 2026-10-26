"""Windows desktop notifier, polling the local Alertmanager inbox without external accounts."""
import ctypes
import json
import time
import urllib.request


def main():
    seen = set()
    while True:
        try:
            events = json.load(urllib.request.urlopen('http://127.0.0.1:8088/api/events', timeout=5))
            if not seen:
                seen.update(e['received_at'] for e in events)
            for e in events:
                if e['received_at'] in seen:
                    continue
                seen.add(e['received_at'])
                payload = e['payload']
                print(e['received_at'], payload.get('status'), flush=True)
                # Console/inbox notification remains available without Windows UI dependencies.
        except (OSError, ValueError):
            pass
        time.sleep(10)


if __name__ == '__main__': main()
