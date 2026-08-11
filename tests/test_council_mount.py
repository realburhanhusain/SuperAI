"""C3.2 — /council must not be advertised unless it is actually mounted."""

import importlib

from fastapi.testclient import TestClient


def _client():
    import cli.web_app as W

    importlib.reload(W)
    return TestClient(W.create_app(), raise_server_exceptions=False)


def _dist_dir():
    from pathlib import Path

    import cli.web_app as W

    return Path(W.__file__).resolve().parents[2] / "projects" / "ai-council" / "frontend" / "dist"


def test_nav_does_not_advertise_council_when_it_is_not_built():
    """
    The regression: frontend/dist is gitignored and built from source, so on a
    clean clone the mount never happens — yet the nav linked /council anyway,
    guaranteeing a 404 for every user.
    """
    dist = _dist_dir()
    if dist.is_dir():  # a local build exists; the negative case cannot be exercised
        import pytest

        pytest.skip("frontend/dist present in this checkout")

    c = _client()
    assert c.get("/council").status_code == 404
    assert "/council" not in c.get("/").text, "nav must not link a route that 404s"


def test_nav_advertises_council_once_it_is_built(tmp_path, monkeypatch):
    """And the converse: when it IS built, the link must come back."""
    dist = _dist_dir()
    created = False
    if not dist.is_dir():
        dist.mkdir(parents=True, exist_ok=True)
        (dist / "index.html").write_text("<!doctype html><h1>council</h1>", encoding="utf-8")
        created = True
    try:
        c = _client()
        assert c.get("/council", follow_redirects=True).status_code == 200
        assert "/council" in c.get("/").text
    finally:
        if created:
            import shutil

            shutil.rmtree(dist, ignore_errors=True)


def test_backend_is_importable_as_a_package():
    """
    backend/main.py uses 12 relative imports and backend/ has __init__.py, so it
    must be imported as `backend.main` with the PARENT on sys.path. Importing
    `main` top-level raised "attempted relative import with no known parent
    package" — which `except Exception: pass` hid entirely, meaning /council
    could never mount even with dist/ built.
    """
    import sys
    from pathlib import Path

    import cli.web_app as W

    council_dir = Path(W.__file__).resolve().parents[2] / "projects" / "ai-council"
    if not (council_dir / "backend" / "__init__.py").is_file():
        import pytest

        pytest.skip("ai-council backend not vendored in this checkout")

    if str(council_dir) not in sys.path:
        sys.path.append(str(council_dir))
    mod = importlib.import_module("backend.main")
    assert hasattr(mod, "app")
