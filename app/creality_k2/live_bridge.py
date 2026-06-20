"""Bridge Creality Print LAN WebSocket (:9999) → SSE for the browser.

Creality Print uses ws://<printer>:9999 with subprotocol ``wsslicer``.
The Pi/Home OS container can reach the printer; browsers connect to our SSE endpoint.
"""
from __future__ import annotations

import json
import logging
import queue
import threading
import time
from typing import Any

import websocket

_LOGGER = logging.getLogger(__name__)

_WS_SUBPROTOCOL = "wsslicer"
_HUBS: dict[str, CrealityLiveHub] = {}
_HUB_LOCK = threading.Lock()


class CrealityLiveHub:
    """One background WS client per printer; fan-out patches to SSE subscribers."""

    def __init__(self, host: str):
        self.host = host
        self.url = f"ws://{host}:9999"
        self._subscribers: list[queue.Queue[dict[str, Any]]] = []
        self._lock = threading.Lock()
        self._data: dict[str, Any] = {}
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name=f"creality-ws-{self.host}", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        backoff = 1.0
        while not self._stop.is_set():
            try:
                ws = websocket.WebSocket()
                ws.connect(self.url, subprotocols=[_WS_SUBPROTOCOL], timeout=10)
                _LOGGER.info("Creality WS connected: %s", self.url)
                backoff = 1.0
                while not self._stop.is_set():
                    raw = ws.recv()
                    if not raw:
                        break
                    patch = json.loads(raw)
                    if not isinstance(patch, dict) or patch.get("method"):
                        continue
                    with self._lock:
                        self._data.update(patch)
                    self._broadcast(patch)
            except Exception as exc:
                _LOGGER.warning("Creality WS error (%s): %s", self.url, exc)
                time.sleep(backoff)
                backoff = min(backoff * 1.6, 30.0)

    def _broadcast(self, patch: dict[str, Any]) -> None:
        with self._lock:
            subs = list(self._subscribers)
        for sub in subs:
            try:
                sub.put_nowait(patch)
            except queue.Full:
                pass

    def subscribe(self) -> queue.Queue[dict[str, Any]]:
        q: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=128)
        with self._lock:
            self._subscribers.append(q)
            snapshot = dict(self._data)
        if snapshot:
            q.put_nowait(snapshot)
        self.start()
        return q

    def unsubscribe(self, q: queue.Queue[dict[str, Any]]) -> None:
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)


def get_live_hub(host: str) -> CrealityLiveHub:
    host = host.strip()
    with _HUB_LOCK:
        hub = _HUBS.get(host)
        if hub is None:
            hub = CrealityLiveHub(host)
            _HUBS[host] = hub
        return hub
