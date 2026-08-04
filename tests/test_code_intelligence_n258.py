import json
import os
import shutil
import tempfile
import time
from pathlib import Path

from core.code_intelligence import index_code_graph, _index_path

def test_cache_rename_deletion_content_edit():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "project"
        root.mkdir()
        cache = Path(td) / "cache"
        cache.mkdir()

        f1 = root / "file1.py"
        f1.write_text("def foo(): pass", encoding="utf-8")
        f2 = root / "file2.py"
        f2.write_text("def bar(): pass", encoding="utf-8")

        g1 = index_code_graph(root, cache_dir=cache)
        assert g1["index"]["mode"] == "full"
        assert len(g1["files"]) == 2

        f2.unlink()
        g2 = index_code_graph(root, cache_dir=cache)
        assert g2["index"]["mode"] == "incremental"
        assert len(g2["files"]) == 1
        assert "file1.py" in g2["files"]

        f1.rename(root / "file3.py")
        g3 = index_code_graph(root, cache_dir=cache)
        assert g3["index"]["mode"] == "incremental"
        assert len(g3["files"]) == 1
        assert "file3.py" in g3["files"]

        f3 = root / "file3.py"
        st = f3.stat()
        f3.write_text("def baz(): pass", encoding="utf-8")
        os.utime(f3, ns=(st.st_atime_ns, st.st_mtime_ns))
        
        g4 = index_code_graph(root, cache_dir=cache)
        assert g4["index"]["mode"] == "cached"

        g5 = index_code_graph(root, cache_dir=cache, verify_content=True)
        assert g5["index"]["mode"] == "incremental"


def test_corrupted_cache_recovery():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "project"
        root.mkdir()
        cache = Path(td) / "cache"
        cache.mkdir()

        f1 = root / "file1.py"
        f1.write_text("def foo(): pass", encoding="utf-8")

        index_code_graph(root, cache_dir=cache)
        
        cache_file = _index_path(root, cache)
        cache_file.write_text("{corrupt json", encoding="utf-8")

        g2 = index_code_graph(root, cache_dir=cache)
        assert g2["index"]["mode"] == "full"


def test_cache_schema_upgrade():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "project"
        root.mkdir()
        cache = Path(td) / "cache"
        cache.mkdir()

        f1 = root / "file1.py"
        f1.write_text("def foo(): pass", encoding="utf-8")

        g1 = index_code_graph(root, cache_dir=cache)
        
        cache_file = _index_path(root, cache)
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        data["version"] = 0
        cache_file.write_text(json.dumps(data), encoding="utf-8")

        g2 = index_code_graph(root, cache_dir=cache)
        assert g2["index"]["mode"] == "full"


def test_maximum_file_limit():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "project"
        root.mkdir()
        cache = Path(td) / "cache"
        cache.mkdir()

        for i in range(5):
            (root / f"file{i}.py").write_text("def foo(): pass", encoding="utf-8")

        g1 = index_code_graph(root, max_files=3, cache_dir=cache)
        assert len(g1["files"]) == 3
