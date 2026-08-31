from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Protocol


class PersistenceConfigurationError(RuntimeError):
    """Raised when a configured persistence provider is unavailable."""


class ObjectStore(Protocol):
    def put_stream(self, key: str, stream: BinaryIO) -> Path: ...
    def path_for(self, key: str) -> Path: ...
    def exists(self, key: str) -> bool: ...
    def delete(self, key: str) -> None: ...


class JsonDocumentStore(Protocol):
    def read(self, key: str) -> Any | None: ...
    def write(self, key: str, value: Any) -> None: ...
    def exists(self, key: str) -> bool: ...
    def delete(self, key: str) -> None: ...


class LocalObjectStore:
    """Development/test object store. Production must use C3-B external storage."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        candidate = (self.root / key).resolve()
        if self.root not in candidate.parents and candidate != self.root:
            raise ValueError("Persistence key escapes the object-store root.")
        return candidate

    def put_stream(self, key: str, stream: BinaryIO) -> Path:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as handle:
            while chunk := stream.read(1024 * 1024):
                handle.write(chunk)
        return path

    def path_for(self, key: str) -> Path:
        return self._path(key)

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


class LocalJsonDocumentStore:
    """Development/test JSON document store with path traversal protection."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        normalized = key if key.endswith(".json") else f"{key}.json"
        candidate = (self.root / normalized).resolve()
        if self.root not in candidate.parents and candidate != self.root:
            raise ValueError("Persistence key escapes the document-store root.")
        return candidate

    def read(self, key: str) -> Any | None:
        path = self._path(key)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def write(self, key: str, value: Any) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2), encoding="utf-8")

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


@dataclass(frozen=True)
class PersistenceContext:
    mode: str
    objects: ObjectStore
    datasets: JsonDocumentStore
    sessions: JsonDocumentStore
    monitoring: JsonDocumentStore
    saved_intelligence: JsonDocumentStore


def json_store(root: Path, *, mode: str = "local") -> JsonDocumentStore:
    if mode == "local":
        return LocalJsonDocumentStore(root)
    if mode == "external":
        raise PersistenceConfigurationError(
            "External production persistence is not implemented until C3-B. "
            "Refusing to fall back to local JSON storage."
        )
    raise PersistenceConfigurationError(f"Unsupported persistence mode: {mode}")


def object_store(root: Path, *, mode: str = "local") -> ObjectStore:
    if mode == "local":
        return LocalObjectStore(root)
    if mode == "external":
        raise PersistenceConfigurationError(
            "External production persistence is not implemented until C3-B. "
            "Refusing to fall back to local object storage."
        )
    raise PersistenceConfigurationError(f"Unsupported persistence mode: {mode}")


def build_local_persistence(runtime_root: Path) -> PersistenceContext:
    return PersistenceContext(
        mode="local",
        objects=LocalObjectStore(runtime_root / "runtime_data"),
        datasets=LocalJsonDocumentStore(runtime_root / "runtime_data"),
        sessions=LocalJsonDocumentStore(runtime_root / "runtime_sessions"),
        monitoring=LocalJsonDocumentStore(runtime_root / "runtime_monitoring"),
        saved_intelligence=LocalJsonDocumentStore(runtime_root / "runtime_saved_intelligence"),
    )


def build_persistence(*, mode: str, runtime_root: Path) -> PersistenceContext:
    if mode == "local":
        return build_local_persistence(runtime_root)
    if mode == "external":
        raise PersistenceConfigurationError(
            "External production persistence is not implemented until C3-B. "
            "Refusing to fall back to local runtime storage."
        )
    raise PersistenceConfigurationError(f"Unsupported persistence mode: {mode}")
