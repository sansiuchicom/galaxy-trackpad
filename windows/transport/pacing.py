"""Play Bluetooth packets back at the Tab's own cadence.

Bluetooth delivers packets in bursts. Injecting on arrival makes the cursor stall
and jump even at 100+ packets/s. Each packet carries the Tab's send time, so we
replay it at that time plus a short delay, in order, on one thread. The delay
follows the jitter actually observed over the last couple of seconds.
"""
from __future__ import annotations

import collections
import ctypes
import threading
import time
from typing import Any

from windows.transport.input_dispatch import InputSession

MIN_DELAY_S = 0.005
MAX_DELAY_S = 0.040
_WINDOW_S = 2.0


class PacedInput:
    def __init__(self) -> None:
        self._queue: collections.deque[tuple[float, dict[str, Any]]] = collections.deque()
        self._cond = threading.Condition()
        self._offsets: collections.deque[tuple[float, float]] = collections.deque()
        self.delay_s = MIN_DELAY_S
        self._closed = False
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, name="bt-pacer", daemon=True)
        self._thread.start()
        self._ready.wait()

    def _due(self, packet: dict[str, Any], now: float) -> float:
        ts = packet.get("timestamp")
        if not isinstance(ts, (int, float)):
            return now
        sent = ts / 1000.0
        self._offsets.append((now, now - sent))
        while now - self._offsets[0][0] > _WINDOW_S:
            self._offsets.popleft()
        # Fastest transit in the window is the baseline; the spread above it is jitter.
        offsets = sorted(o for _, o in self._offsets)
        base = offsets[0]
        p95 = offsets[min(len(offsets) - 1, int(len(offsets) * 0.95))] - base
        self.delay_s = min(MAX_DELAY_S, max(MIN_DELAY_S, p95 + 0.002))
        return max(now, sent + base + self.delay_s)

    def apply_packet(self, packet: dict[str, Any]) -> None:
        now = time.monotonic()
        with self._cond:
            due = self._due(packet, now)
            if self._queue and due < self._queue[-1][0]:
                due = self._queue[-1][0]
            self._queue.append((due, packet))
            self._cond.notify()

    def _run(self) -> None:
        winmm = ctypes.WinDLL("winmm")
        # Default Windows wait granularity is ~15.6 ms, which would reintroduce the stutter.
        winmm.timeBeginPeriod(1)
        session = InputSession()
        self._ready.set()
        try:
            while True:
                with self._cond:
                    while not self._queue and not self._closed:
                        self._cond.wait()
                    if self._closed:
                        return
                    due, packet = self._queue[0]
                    wait = due - time.monotonic()
                    if wait > 0:
                        self._cond.wait(wait)
                        continue
                    self._queue.popleft()
                session.apply_packet(packet)
        finally:
            session.close()
            winmm.timeEndPeriod(1)

    def close(self) -> None:
        with self._cond:
            self._closed = True
            self._cond.notify()
        self._thread.join(2.0)
