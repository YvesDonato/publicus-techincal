from __future__ import annotations

import sys
from pathlib import Path

from publicus_backend.app import app


def run() -> None:
    import uvicorn

    backend_dir = str(Path(__file__).resolve().parents[1])
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    uvicorn.run("publicus_backend.app:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    run()

