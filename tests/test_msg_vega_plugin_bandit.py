"""Messengers, Vega charts, plugin registry, bandit-router wiring."""

from pathlib import Path

import pytest

from core.bandit_router import EpsilonGreedyBandit
from core.messengers import MessengerBus
from core.model_registry import ModelRegistry
from core.model_router import ModelRouter
from core.load_balancer import LoadBalancer
from core.plugin_registry import PluginRegistry
from core.vega_charts import chart_from_table, render_vega_html, write_chart_html


def test_telegram_slack_dry_run(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_MESSENGER_DRY_RUN", "1")
    monkeypatch.delenv("SUPERAI_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SUPERAI_SLACK_WEBHOOK_URL", raising=False)
    bus = MessengerBus(path=tmp_path / "log.jsonl")
    channels = bus.list_channels()
    assert channels["telegram"]["enabled"] is True
    assert channels["slack"]["enabled"] is True

    tg = bus.send("hello telegram", channel="telegram")
    assert tg["ok"] is True
    assert tg.get("dry_run") or (tg.get("entry") or {}).get("dry_run")

    sl = bus.send("hello slack", channel="slack")
    assert sl["ok"] is True

    bc = bus.broadcast("hi all", channels=["file", "telegram"])
    assert bc["ok"] is True
    assert "file" in bc["results"]


def test_vega_html_render(tmp_path: Path):
    spec = chart_from_table(
        ["country", "revenue"],
        [["DE", 100], ["US", 200]],
        title="Revenue",
    )
    html = render_vega_html(spec, title="Revenue by country")
    assert "vegaEmbed" in html
    assert "Revenue by country" in html
    assert "bar" in html

    path = write_chart_html(spec, path=tmp_path / "c.html", title="T")
    assert path.exists()
    assert "vega-lite" in path.read_text(encoding="utf-8")


def test_plugin_registry_lifecycle(tmp_path: Path):
    reg = PluginRegistry(root=tmp_path / "plugins")
    summary = reg.marketplace_summary()
    assert summary["total"] >= 5
    plugins = reg.list_plugins()
    assert any(p["id"] == "core.council" for p in plugins)

    found = reg.search("messenger")
    assert found

    # Install local plugin
    manifest = {
        "id": "local.demo",
        "name": "Demo Plugin",
        "version": "1.0.0",
        "category": "example",
        "description": "Installed for tests",
        "status": "installed",
    }
    installed = reg.install_manifest(manifest)
    assert installed["id"] == "local.demo"
    assert (tmp_path / "plugins" / "local.demo" / "plugin.json").exists()

    reg.disable("local.demo")
    p = reg.get("local.demo")
    assert p is not None
    assert p["enabled"] is False
    reg.enable("local.demo")
    assert reg.get("local.demo")["enabled"] is True

    reg.uninstall("local.demo")
    assert reg.get("local.demo") is None or reg.get("local.demo")["id"] != "local.demo"


def test_bandit_wired_into_router(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_USE_BANDIT", "1")
    bandit = EpsilonGreedyBandit(epsilon=0.0, path=tmp_path / "bandit.json")
    # Strong preference for one model via rewards
    for _ in range(5):
        bandit.update("claude-4-sonnet", 0.95)
        bandit.update("gpt-4o", 0.1)

    registry = ModelRegistry()
    router = ModelRouter(
        registry,
        LoadBalancer(),
        bandit=bandit,
        use_bandit=True,
        bandit_blend=0.5,
    )
    # Forced preferred still wins
    name = router.select_model("write code", preferred_model="gpt-4o")
    assert name == "gpt-4o"

    # Without preferred, selection should work and update bandit
    best = router.get_best_model("Implement a FastAPI endpoint")
    assert best is not None
    reward = router.update_bandit(best.name, success=True, latency=0.5, cost=0.01)
    assert reward is not None
    assert reward > 0
    assert best.name in bandit.state


def test_web_charts_and_plugins(tmp_path: Path, monkeypatch):
    pytest.importorskip("fastapi")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    from fastapi.testclient import TestClient
    from scli.web_app import create_app

    client = TestClient(create_app())
    r = client.get("/charts")
    assert r.status_code == 200
    assert "Vega" in r.text

    spec = chart_from_table(["x", "y"], [["a", 1], ["b", 2]])
    r2 = client.post("/api/charts/render", json={"spec": spec, "title": "T"})
    assert r2.status_code == 200
    assert "vegaEmbed" in r2.text

    r3 = client.get("/api/plugins")
    assert r3.status_code == 200
    body = r3.json()
    assert "plugins" in body
    assert body["summary"]["total"] >= 1

    r4 = client.get("/api/bandit")
    assert r4.status_code == 200
    assert "arms" in r4.json()
