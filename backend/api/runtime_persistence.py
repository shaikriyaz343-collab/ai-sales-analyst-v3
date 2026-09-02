from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import settings
from .persistence import (
    LocalJsonDocumentStore,
    LocalObjectStore,
    PersistenceContext,
    build_persistence,
)


class PsycopgConnectionPool:
    def __init__(self, database_url: str):
        self.database_url = database_url
        try:
            import psycopg_pool
        except ImportError as exc:
            raise RuntimeError("psycopg_pool is required for connection pooling.") from exc
        self._pool = psycopg_pool.ConnectionPool(self.database_url, open=False)
        self._closed = False

    def open(self):
        self._pool.open(wait=True)
        self.check()

    def check(self):
        with self.connection() as conn:
            conn.execute("SELECT 1")

    def close(self):
        if not self._closed:
            self._pool.close()
            self._closed = True

    def connection(self):
        return self._pool.connection()


_context: PersistenceContext | None = None
_provider: PsycopgConnectionPool | None = None

def get_runtime_persistence() -> PersistenceContext:
    """Return one process-local PersistenceContext for the configured mode."""
    global _context
    if _context is None:
        if settings.persistence_mode == "external":
            raise RuntimeError("External runtime persistence was accessed before lifecycle startup.")
        _context = build_persistence(
            mode="local",
            runtime_root=settings.runtime_root,
        )
    return _context

def start_runtime_persistence() -> PersistenceContext:
    """Initialize external runtime persistence explicitly during startup."""
    global _context, _provider
    if _context is not None:
        return _context

    if settings.persistence_mode != "external":
        return get_runtime_persistence()

    _provider = PsycopgConnectionPool(settings.database_url)
    try:
        _provider.open()
        _context = build_persistence(
            mode=settings.persistence_mode,
            runtime_root=settings.runtime_root,
            database_url=settings.database_url,
            provider=_provider,
            object_bucket=settings.object_store_bucket,
            object_region=settings.object_store_region,
            object_endpoint_url=settings.object_store_endpoint_url,
            object_access_key=settings.object_store_access_key,
            object_secret_key=settings.object_store_secret_key,
            object_prefix=settings.object_store_prefix,
            object_temp_root=settings.object_store_temp_root,
        )
    except Exception:
        _provider.close()
        _provider = None
        raise
    return _context

def reset_runtime_persistence() -> None:
    """Reset the process-local registry for test isolation and shutdown."""
    global _context, _provider
    _context = None
    if _provider is not None:
        _provider.close()
        _provider = None


def runtime_document_store(namespace: str, *, local_root: Path) -> Any:
    """Return the configured document store for an application namespace."""
    context = get_runtime_persistence()
    if context.mode == "local":
        return LocalJsonDocumentStore(local_root)

    stores = {
        "datasets": context.datasets,
        "sessions": context.sessions,
        "monitoring": context.monitoring,
        "saved_intelligence": context.saved_intelligence,
    }
    try:
        return stores[namespace]
    except KeyError as exc:
        raise ValueError(f"Unsupported runtime document namespace: {namespace}") from exc


def runtime_object_store(*, local_root: Path) -> Any:
    """Return the configured object store for application file operations."""
    context = get_runtime_persistence()
    if context.mode == "local":
        return LocalObjectStore(local_root)
    return context.objects
