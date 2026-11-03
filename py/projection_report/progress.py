"""Progress reporting from Python to the web UI."""

import json
from typing import Callable

# Called as progress(stage, done, total); total is 0 when unknown.
ProgressCallback = Callable[[str, int, int], None]

# The UI watches the worker's stdout for lines that start with this.
PROGRESS_PREFIX = "PROGRESS "


def print_progress(stage: str, done: int, total: int) -> None:
    """Write a progress line to stdout for the web UI."""
    print(PROGRESS_PREFIX + json.dumps({"stage": stage, "done": done, "total": total}), flush=True)
