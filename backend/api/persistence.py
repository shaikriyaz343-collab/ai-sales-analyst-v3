from __future__ import annotations

import json
import hashlib
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Callable, Protocol

from .config import settings


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
    provider: Any | None = None


class PostgresJsonDocumentStore:
    _TABLE = "v4_json_documents"
    def __init__(self,database_url:str,namespace:str,connect:Callable[...,Any]|None=None,provider:Any|None=None)->None:
        if not database_url and not provider: raise PersistenceConfigurationError("V4_DATABASE_URL is required for external persistence.")
        self.database_url=database_url; self.namespace=namespace; self._connect_factory=connect; self.provider=provider; self._ensure_table()
    def _connect(self):
        if self.provider is not None: return self.provider.connection()
        if self._connect_factory is not None: return self._connect_factory(self.database_url)
        try: import psycopg
        except ImportError as exc: raise PersistenceConfigurationError("psycopg is required for external PostgreSQL persistence.") from exc
        return psycopg.connect(self.database_url)
    @staticmethod
    def _json_adapter(value:Any)->Any:
        try: from psycopg.types.json import Json
        except ImportError as exc: raise PersistenceConfigurationError("psycopg is required for external PostgreSQL persistence.") from exc
        return Json(value)
    def _ensure_table(self)->None:
        with self._connect() as conn:
            conn.execute(f"CREATE TABLE IF NOT EXISTS {self._TABLE} (namespace TEXT NOT NULL, document_key TEXT NOT NULL, payload JSONB NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), PRIMARY KEY(namespace, document_key))"); conn.commit()
    def read(self,key:str)->Any|None:
        with self._connect() as conn:
            row=conn.execute(f"SELECT payload FROM {self._TABLE} WHERE namespace=%s AND document_key=%s",(self.namespace,key)).fetchone(); return None if row is None else row[0]
    def write(self,key:str,value:Any)->None:
        with self._connect() as conn:
            conn.execute(f"INSERT INTO {self._TABLE}(namespace,document_key,payload,updated_at) VALUES(%s,%s,%s,NOW()) ON CONFLICT(namespace,document_key) DO UPDATE SET payload=EXCLUDED.payload,updated_at=NOW()",(self.namespace,key,self._json_adapter(value))); conn.commit()
    def exists(self,key:str)->bool:
        with self._connect() as conn: return conn.execute(f"SELECT 1 FROM {self._TABLE} WHERE namespace=%s AND document_key=%s LIMIT 1",(self.namespace,key)).fetchone() is not None
    def delete(self,key:str)->None:
        with self._connect() as conn: conn.execute(f"DELETE FROM {self._TABLE} WHERE namespace=%s AND document_key=%s",(self.namespace,key)); conn.commit()

class S3ObjectStore:
    def __init__(self,bucket:str,region:str,endpoint_url:str|None=None,access_key:str|None=None,secret_key:str|None=None,prefix:str="",temp_root:Path|None=None,client:Any|None=None)->None:
        if not bucket or not region: raise PersistenceConfigurationError("V4_OBJECT_STORE_BUCKET and V4_OBJECT_STORE_REGION are required for external persistence.")
        self.bucket=bucket; self.region=region; self.prefix=prefix.strip("/"); self.temp_root=(temp_root or Path(tempfile.gettempdir())/"ai-sales-analyst-v4-objects").resolve(); self.temp_root.mkdir(parents=True,exist_ok=True)
        self._cleanup_orphaned_tmps()
        if client is not None: self.client=client; return
        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc: raise PersistenceConfigurationError("boto3 is required for external S3-compatible object storage.") from exc

        boto_config = Config(
            connect_timeout=settings.object_store_timeout_connect,
            read_timeout=settings.object_store_timeout_read,
            retries={'max_attempts': 3}
        )
        kwargs={'region_name':region, 'config': boto_config}
        if endpoint_url: kwargs['endpoint_url']=endpoint_url
        if access_key: kwargs['aws_access_key_id']=access_key
        if secret_key: kwargs['aws_secret_access_key']=secret_key
        self.client=boto3.client('s3',**kwargs)
    def _key(self,key:str)->str:
        clean=key.replace('\\','/').lstrip('/')
        if any(part=='..' for part in clean.split('/')): raise ValueError('Persistence key cannot contain parent-directory segments.')
        return f'{self.prefix}/{clean}' if self.prefix else clean
    def _cache_path(self,key:str)->Path:
        return self.temp_root/f"{hashlib.sha256(self._key(key).encode()).hexdigest()}{Path(key).suffix}"

    def _cleanup_orphaned_tmps(self):
        for p in self.temp_root.glob("*.tmp"):
            try:
                p.unlink()
            except FileNotFoundError:
                pass
            except PermissionError as exc:
                if getattr(exc, 'winerror', None) == 32:
                    pass
                else:
                    raise

    def _update_recency(self, path: Path):
        try:
            import time, os
            now = time.time()
            os.utime(path, (now, now))
        except OSError: pass

    def _evict_if_needed(self):
        import os
        from backend.api.config import settings
        cap = settings.cache_max_bytes

        files_with_stats = []
        for p in self.temp_root.iterdir():
            if p.is_file() and not p.name.endswith(".tmp"):
                try:
                    stat = p.stat()
                    files_with_stats.append((p, stat.st_size, stat.st_mtime))
                except FileNotFoundError: pass

        total_bytes = sum(size for _, size, _ in files_with_stats)
        if total_bytes <= cap: return

        files_with_stats.sort(key=lambda x: x[2])
        for p, size, _ in files_with_stats:
            if total_bytes <= cap: break
            try:
                p.unlink()
                total_bytes -= size
            except (FileNotFoundError, PermissionError) as exc:
                if isinstance(exc, PermissionError):
                    if getattr(exc, 'winerror', None) == 32: continue
                    raise
                total_bytes -= size

    def put_stream(self,key:str,stream:BinaryIO)->Path:
        import uuid
        cache = self._cache_path(key)
        temp_path = self.temp_root / f"{cache.name}.{uuid.uuid4().hex}.tmp"
        try:
            with temp_path.open("wb") as handle:
                while chunk := stream.read(1024 * 1024):
                    handle.write(chunk)
            self.client.upload_file(str(temp_path), self.bucket, self._key(key))
            temp_path.replace(cache)
        finally:
            temp_path.unlink(missing_ok=True)
        self._update_recency(cache)
        self._evict_if_needed()
        return cache
    def path_for(self,key:str)->Path:
        cache=self._cache_path(key)
        if not cache.exists():
            import uuid
            import botocore.exceptions
            temp_path = self.temp_root/f"{cache.name}.{uuid.uuid4().hex}.tmp"
            try:
                self.client.download_file(self.bucket,self._key(key),str(temp_path))
                try:
                    temp_path.replace(cache)
                except OSError:
                    if cache.exists() and cache.stat().st_size == temp_path.stat().st_size:
                        pass
                    else:
                        raise
            except Exception as exc:
                if isinstance(exc, botocore.exceptions.ClientError) and exc.response.get("Error", {}).get("Code") == "404":
                    raise ValueError("Dataset file is no longer available for analysis.") from exc
                raise
            finally:
                temp_path.unlink(missing_ok=True)
        self._update_recency(cache)
        self._evict_if_needed()
        return cache
    def exists(self,key:str)->bool:
        try: self.client.head_object(Bucket=self.bucket,Key=self._key(key)); return True
        except Exception as exc:
            import botocore.exceptions
            if isinstance(exc, botocore.exceptions.ClientError) and exc.response.get("Error", {}).get("Code") == "404": return False
            raise PersistenceConfigurationError(f"Object-store object is unavailable: {key}") from exc
    def delete(self,key:str)->None:
        self.client.delete_object(Bucket=self.bucket,Key=self._key(key)); self._cache_path(key).unlink(missing_ok=True)

def build_external_persistence(*,database_url:str,object_bucket:str,object_region:str,object_endpoint_url:str|None,object_access_key:str|None,object_secret_key:str|None,object_prefix:str,object_temp_root:Path,provider:Any|None=None)->PersistenceContext:
    return PersistenceContext(mode='external',objects=S3ObjectStore(object_bucket,object_region,object_endpoint_url,object_access_key,object_secret_key,object_prefix,object_temp_root),datasets=PostgresJsonDocumentStore(database_url,'datasets',provider=provider),sessions=PostgresJsonDocumentStore(database_url,'sessions',provider=provider),monitoring=PostgresJsonDocumentStore(database_url,'monitoring',provider=provider),saved_intelligence=PostgresJsonDocumentStore(database_url,'saved_intelligence',provider=provider),provider=provider)

def build_persistence(*,mode:str,runtime_root:Path,database_url:str|None=None,object_bucket:str|None=None,object_region:str|None=None,object_endpoint_url:str|None=None,object_access_key:str|None=None,object_secret_key:str|None=None,object_prefix:str='',object_temp_root:Path|None=None,provider:Any|None=None)->PersistenceContext:
    if mode=='local': return build_local_persistence(runtime_root)
    if mode=='external':
        if not database_url or not object_bucket or not object_region: raise PersistenceConfigurationError('External persistence requires PostgreSQL URL, object-store bucket, and object-store region.')
        return build_external_persistence(database_url=database_url,object_bucket=object_bucket,object_region=object_region,object_endpoint_url=object_endpoint_url,object_access_key=object_access_key,object_secret_key=object_secret_key,object_prefix=object_prefix,object_temp_root=object_temp_root or Path(tempfile.gettempdir())/'ai-sales-analyst-v4-objects',provider=provider)
    raise PersistenceConfigurationError(f'Unsupported persistence mode: {mode}')

def build_local_persistence(runtime_root: Path) -> PersistenceContext:
    return PersistenceContext(
        mode="local",
        objects=LocalObjectStore(runtime_root / "runtime_data"),
        datasets=LocalJsonDocumentStore(runtime_root / "runtime_data"),
        sessions=LocalJsonDocumentStore(runtime_root / "runtime_sessions"),
        monitoring=LocalJsonDocumentStore(runtime_root / "runtime_monitoring"),
        saved_intelligence=LocalJsonDocumentStore(runtime_root / "runtime_saved_intelligence"),
    )


def json_store(root:Path,*,mode:str='local')->JsonDocumentStore:
    if mode=='local': return LocalJsonDocumentStore(root)
    raise PersistenceConfigurationError("External JSON storage is provided through build_persistence().")

def object_store(root:Path,*,mode:str='local')->ObjectStore:
    if mode=='local': return LocalObjectStore(root)
    raise PersistenceConfigurationError("External object storage is provided through build_persistence().")
