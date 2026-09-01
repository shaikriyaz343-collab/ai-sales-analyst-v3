from io import BytesIO
from pathlib import Path
import pytest
from backend.api.persistence import S3ObjectStore, PersistenceConfigurationError, build_persistence

class FakeS3:
    def __init__(self): self.objects={}
    def upload_fileobj(self,s,b,k): self.objects[(b,k)]=s.read()
    def download_file(self,b,k,f): Path(f).write_bytes(self.objects[(b,k)])
    def head_object(self,Bucket,Key):
        if (Bucket,Key) not in self.objects: raise KeyError(Key)
    def delete_object(self,Bucket,Key): self.objects.pop((Bucket,Key),None)

def test_s3_adapter_round_trip(tmp_path):
    c=FakeS3(); s=S3ObjectStore("b","ap-south-1",prefix="v4",temp_root=tmp_path,client=c)
    p=s.put_stream("dataset.csv",BytesIO(b"a,b\n1,2\n")); assert p.read_bytes()==b"a,b\n1,2\n"; assert s.exists("dataset.csv"); s.delete("dataset.csv"); assert not s.exists("dataset.csv")

def test_s3_adapter_rejects_parent_segment(tmp_path):
    s=S3ObjectStore("b","ap-south-1",temp_root=tmp_path,client=FakeS3())
    with pytest.raises(ValueError,match="parent-directory"): s.path_for("../secret.csv")

def test_external_build_requires_configuration(tmp_path):
    with pytest.raises(PersistenceConfigurationError,match="PostgreSQL URL"):
        build_persistence(mode="external",runtime_root=tmp_path,database_url=None,object_bucket="b",object_region="r")
