"""Memory Roadmap P5 — multi-format ingest tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.ingest import (
    chunk_text,
    detect_format,
    extract_pdf_text_basic,
    formats_matrix,
    ingest,
    load_jsonl_text,
    load_local_file,
    strip_html,
)
from core.knowledge_graph import KnowledgeGraph
from core.net_safety import validate_public_http_url

pytestmark = pytest.mark.unit


def _minimal_pdf(text: str) -> bytes:
    """Build a tiny PDF with one Tj text operator (basic extractor target)."""
    # Escape PDF string specials
    esc = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 50 50 Td ({esc}) Tj ET"
    stream_bytes = stream.encode("latin-1")
    objs = []
    objs.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objs.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objs.append(
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] "
        b"/Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj\n"
    )
    objs.append(
        f"4 0 obj<< /Length {len(stream_bytes)} >>stream\n".encode("latin-1")
        + stream_bytes
        + b"\nendstream\nendobj\n"
    )
    objs.append(
        b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n"
    )
    body = b"".join(objs)
    # Simple xref omitted — basic extractor only needs stream text
    return b"%PDF-1.1\n" + body + b"\ntrailer<< /Root 1 0 R >>\n%%EOF\n"


@pytest.fixture
def iso(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    monkeypatch.setenv("SUPERAI_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("SUPERAI_KG_DSN", f"sqlite:///{(tmp_path / 'kg.sqlite').as_posix()}")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    mem = tmp_path / ".superai" / "memory"
    mem.mkdir(parents=True)
    monkeypatch.setenv(
        "SUPERAI_MEMORY_DSN", f"sqlite:///{(mem / 'palace.sqlite').as_posix()}"
    )
    return tmp_path


def test_formats_matrix_has_pdf_url_md():
    names = {r["format"] for r in formats_matrix()}
    assert "markdown" in names
    assert "pdf" in names
    assert "url" in names
    assert "jsonl" in names


def test_detect_format():
    assert detect_format("x.md") == "markdown"
    assert detect_format("x.pdf") == "pdf"
    assert detect_format("x.jsonl") == "jsonl"
    assert detect_format("https://example.com/a") == "url"


def test_chunk_text_overlap():
    text = "a" * 5000
    chunks = chunk_text(text, chunk_size=1000, overlap=100)
    assert len(chunks) >= 5
    assert all(len(c) <= 1000 for c in chunks)


def test_strip_html():
    assert "hello" in strip_html("<p>hello <b>world</b></p>").lower()


def test_jsonl_load():
    raw = '{"text":"Cloud SQL uses Dataplex."}\n{"content":"Policy Tags protects data."}\n'
    text, label, meta = load_jsonl_text(raw)
    assert label == "jsonl"
    assert "Cloud SQL" in text
    assert "Policy Tags" in text
    assert meta.get("invalid_lines") == 0

    bad = '{"ok":true}\nnot-json\n{"x":1}\n'
    text2, label2, meta2 = load_jsonl_text(bad)
    assert label2 == "jsonl"
    assert meta2.get("invalid_lines") == 1
    assert "not-json" not in text2


def test_pdf_basic_extractor():
    data = _minimal_pdf("Hello Cloud SQL Banking App")
    out = extract_pdf_text_basic(data)
    assert "Cloud SQL" in out


def test_ssrf_blocks_localhost():
    err = validate_public_http_url("http://127.0.0.1/secret")
    assert err is not None
    err2 = validate_public_http_url("http://localhost/x")
    assert err2 is not None


def test_ingest_url_ssrf_blocked(iso: Path):
    rep = ingest(url="http://127.0.0.1/admin", dry_run=True, store_palace=False)
    assert rep["ok"] is False
    assert rep.get("error_code") == "ssrf"


def test_ingest_url_mocked_fetch(iso: Path):
    def fake_fetch(url: str):
        return {
            "ok": True,
            "text": "Cloud SQL uses Dataplex for catalog.",
            "content_type": "text/plain",
            "bytes": 40,
        }

    # Use a public hostname that passes SSRF DNS only if resolvable —
    # inject after validate by using allow_private + mock is cleaner:
    # fetch_url_text validates first. Use example.com (public) with mock fetcher.
    rep = ingest(
        url="https://example.com/doc",
        fetch_fn=fake_fetch,
        dry_run=True,
        store_palace=False,
        enforce_jail=True,
    )
    # example.com should resolve public
    if rep.get("error_code") == "ssrf":
        pytest.skip(f"SSRF blocked example.com in this env: {rep.get('error')}")
    assert rep["ok"] is True
    assert rep["dry_run"] is True
    assert "url" in rep.get("formats", [])


def test_workspace_jail_blocks_outside(iso: Path, monkeypatch):
    monkeypatch.delenv("SUPERAI_INGEST_ALLOW_OUTSIDE", raising=False)
    outside = Path("C:/Windows/System32/drivers/etc/hosts")
    if not outside.is_file():
        pytest.skip("no outside file available")
    loaded = load_local_file(outside, enforce_jail=True)
    assert loaded["ok"] is False
    assert loaded.get("error_code") == "workspace_jail"


def test_ingest_markdown_to_palace(iso: Path):
    doc = iso / "notes.md"
    doc.write_text(
        "# Banking\n\nCloud SQL uses Dataplex.\nPolicy Tags protects Cloud SQL.\n",
        encoding="utf-8",
    )
    rep = ingest(
        str(doc),
        dataset_id="p5test",
        store_palace=True,
        cognify=False,
        dry_run=False,
        enforce_jail=True,
    )
    assert rep["ok"] is True
    assert rep["chunks_written"] >= 1
    assert "markdown" in rep["formats"]


def test_ingest_pdf_and_cognify(iso: Path):
    pdf_path = iso / "note.pdf"
    pdf_path.write_bytes(_minimal_pdf("Banking App uses Cloud SQL."))
    kg = KnowledgeGraph(lock_root=iso)
    rep = ingest(
        str(pdf_path),
        dataset_id="p5pdf",
        store_palace=False,
        cognify=True,
        cognify_mode="mock",
        dry_run=False,
        enforce_jail=True,
        kg=kg,
    )
    assert rep["ok"] is True
    assert "pdf" in rep["formats"]
    # cognify may extract entities depending on text harvest quality
    assert rep.get("items_ok", 0) >= 1
    item = rep["items"][0]
    assert item.get("ok") is True
    assert "cognify" in item


def test_ingest_jsonl_file(iso: Path):
    p = iso / "rows.jsonl"
    p.write_text(
        '{"text":"Alice owns Banking App."}\n{"text":"Banking App uses Cloud SQL."}\n',
        encoding="utf-8",
    )
    rep = ingest(str(p), dry_run=True, store_palace=False, enforce_jail=True)
    assert rep["ok"] is True
    assert "jsonl" in rep["formats"]
    assert rep["items"][0]["chars"] > 10


def test_ingest_dir_glob(iso: Path):
    d = iso / "docs"
    d.mkdir()
    (d / "a.md").write_text("Cloud SQL is a System.\n", encoding="utf-8")
    (d / "b.md").write_text("Dataplex is a System.\n", encoding="utf-8")
    (d / "skip.txt").write_text("ignored by default glob\n", encoding="utf-8")
    rep = ingest(
        str(d),
        glob_pat="*.md",
        dry_run=True,
        store_palace=False,
        enforce_jail=True,
    )
    assert rep["ok"] is True
    assert rep["items_total"] == 2
