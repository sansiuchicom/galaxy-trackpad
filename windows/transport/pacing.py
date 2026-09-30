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
from typing import Any, Callable

from windows.transport.input_dispatch import InputSession

MIN_DELAY_S = 0.005
MAX_DELAY_S = 0.025
# Smooth the common case; rarer late packets are applied on arrival instead of delaying everything.
JITTER_PERCENTILE = 0.80
_WINDOW_S = 2.0


class PacedInput:
    def __init__(
        self,
        max_delay_s: float = MAX_DELAY_S,
        percentile: float = JITTER_PERCENTILE,
        sink: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        """Without a sink, owns an InputSession; with one, forwards packets to it."""
        self._sink = sink
        self._max_delay = max_delay_s
        self._percentile = percentile
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
        jitter = offsets[min(len(offsets) - 1, int(len(offsets) * self._percentile))] - base
        self.delay_s = min(self._max_delay, max(MIN_DELAY_S, jitter + 0.002))
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
        session = InputSession() if self._sink is None else None
        apply = self._sink or session.apply_packet
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
                try:
                    apply(packet)
                except Exception:  # noqa: BLE001 - one bad packet must not stop input
                    pass
        finally:
            if session is not None:
                session.close()
            winmm.timeEndPeriod(1)

    def close(self) -> None:
        with self._cond:
            self._closed = True
            self._cond.notify()
        self._thread.join(2.0)
