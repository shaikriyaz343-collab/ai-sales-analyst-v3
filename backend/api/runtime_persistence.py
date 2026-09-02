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


_context: PersistenceContext | None = None


def get_runtime_persistence() -> PersistenceContext:
    """Return one process-local PersistenceContext for the configured mode."""
    global _context
    if _context is None:
        _context = build_persistence(
            mode=settings.persistence_mode,
            runtime_root=settings.runtime_root,
            database_url=settings.database_url,
            object_bucket=settings.object_store_bucket,
            object_region=settings.object_store_region,
            object_endpoint_url=settings.object_store_endpoint_url,
            object_access_key=settings.object_store_access_key,
            object_secret_key=settings.object_store_secret_key,
            object_prefix=settings.object_store_prefix,
            object_temp_root=settings.object_store_temp_root,
        )
    return _context


def reset_runtime_persistence() -> None:
    """Reset the process-local registry for test isolation."""
    global _context
    _context = None


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
