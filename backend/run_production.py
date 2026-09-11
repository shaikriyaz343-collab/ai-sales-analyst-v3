from __future__ import annotations

import os

import uvicorn


def main() -> None:
    """Start the V4 FastAPI service as a single non-reload process."""
    host = os.getenv("V4_BIND_HOST", "127.0.0.1")
    port = int(os.getenv("V4_BIND_PORT", "8000"))

    uvicorn.run(
        "backend.api.main:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
