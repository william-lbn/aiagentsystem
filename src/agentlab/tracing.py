from contextlib import contextmanager
from time import perf_counter, time


class TraceRecorder:
    def __init__(self):
        self.spans = []

    @contextmanager
    def span(self, name: str, **attrs):
        t0 = perf_counter()
        started = time()
        try:
            yield
        finally:
            self.spans.append(
                {
                    "name": name,
                    "started": started,
                    "duration_ms": round((perf_counter() - t0) * 1000, 3),
                    "attrs": attrs,
                }
            )
