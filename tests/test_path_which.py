"""Windows-aware PATH resolution."""

from core.path_which import which_cmd, which_any


def test_which_python_or_none():
    # python should exist in this environment
    p = which_cmd("python") or which_any(["python", "python3", "py"])
    assert p is None or isinstance(p, str)
