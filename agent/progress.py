import sys
import time


class StepTracker:
    """Prints numbered steps with elapsed time."""

    def __init__(self):
        self._step = 0
        self._start = None

    def step(self, msg: str):
        self._finish_prev()
        self._step += 1
        self._start = time.time()
        sys.stdout.write(f"  [{self._step}] {msg}...")
        sys.stdout.flush()

    def _finish_prev(self):
        if self._start is not None:
            elapsed = time.time() - self._start
            print(f" done ({elapsed:.1f}s)")

    def done(self):
        self._finish_prev()
        self._start = None
        print()
