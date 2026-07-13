"""
Minimal FastAPI web surface for SuperAI (memory query + status).

Run:
  pip install -e ".[web]"
  superai web
  # or: uvicorn superai.web_app:app --reload --port 8787
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

try:
    from fastapi import FastAPI, HTTPException, Query, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    from pydantic import BaseModel, Field

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    FastAPI = object  # type: ignore
    BaseModel = object  # type: ignore
    Request = object  # type: ignore


def create_app() -> Any:
    if not HAS_FASTAPI:
        raise RuntimeError(
            "FastAPI not installed. Run: pip install -e \".[web]\" "
            "or pip install fastapi uvicorn"
        )

    app = FastAPI(
        title="SuperAI Web",
        version="0.1.0",
        description="Memory query + status API for SuperAI",
    )

    class MemoryQuery(BaseModel):
        query: str = Field(..., min_length=1)
        top_k: int = Field(8, ge=1, le=50)
        tags: Optional[str] = Field(
            None, description="Comma-separated tags filter"
        )

    class PreferenceBody(BaseModel):
        key: str
        value: Any

    @app.get("/", response_class=HTMLResponse)
    def home() -> str:
        return """<!doctype html>
<html><head><meta charset="utf-8"><title>SuperAI Memory</title>
<style>
 body{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem}
 input,button{font-size:1rem;padding:.5rem}
 #out{white-space:pre-wrap;background:#f6f8fa;padding:1rem;border-radius:8px}
 .card{border:1px solid #ddd;border-radius:8px;padding:.75rem;margin:.5rem 0}
</style></head>
<body>
<h1>SuperAI Memory Query</h1>
<p>Shared surface for terminal + web (Mempalace-inspired).</p>
<p>
<input id="q" size="50" placeholder="Search memories..."/>
<button onclick="go()">Search</button>
<button onclick="status()">Status</button>
</p>
<div id="out">Ready.</div>
<script>
async function go(){
  const q=document.getElementById('q').value;
  const r=await fetch('/api/memory/search?q='+encodeURIComponent(q)+'&top_k=8');
  const j=await r.json();
  let html='';
  (j.results||[]).forEach(m=>{
    html+='<div class="card"><b>'+(m.id||'')+'</b><br/>'+
      (m.content||'').slice(0,400)+'<br/><small>'+
      JSON.stringify(m.metadata||{})+'</small></div>';
  });
  document.getElementById('out').innerHTML=html||JSON.stringify(j,null,2);
}
async function status(){
  const r=await fetch('/api/status');
  document.getElementById('out').textContent=JSON.stringify(await r.json(),null,2);
}
</script>
</body></html>"""

    @app.get("/api/status")
    def api_status() -> Dict[str, Any]:
        from superai import __version__
        from superai.core.config import Config
        from superai.core.history import TaskHistory
        from superai.core.memory_palace import MemoryPalace
        from superai.core.preferences import UserPreferenceModel

        cfg = Config()
        mp = MemoryPalace()
        return {
            "version": __version__,
            "mock_mode": cfg.use_mock,
            "history": TaskHistory().count(),
            "memory": mp.get_memory_stats(),
            "preferences": UserPreferenceModel().profile_summary(),
        }

    @app.get("/api/memory/search")
    def memory_search(
        q: str = Query(..., min_length=1),
        top_k: int = Query(8, ge=1, le=50),
        tags: Optional[str] = None,
    ) -> Dict[str, Any]:
        from superai.core.memory_palace import MemoryPalace

        tag_list = [t.strip() for t in tags.split(",")] if tags else None
        mp = MemoryPalace()
        results = mp.query_semantic(q, top_k=top_k, tags=tag_list)
        return {"query": q, "count": len(results), "results": results}

    @app.post("/api/memory/search")
    def memory_search_post(body: MemoryQuery) -> Dict[str, Any]:
        return memory_search(body.query, body.top_k, body.tags)

    @app.get("/api/preferences")
    def get_prefs() -> Dict[str, Any]:
        from superai.core.preferences import UserPreferenceModel

        return UserPreferenceModel().profile_summary()

    @app.post("/api/preferences")
    def set_pref(body: PreferenceBody) -> Dict[str, Any]:
        from superai.core.preferences import UserPreferenceModel

        pm = UserPreferenceModel()
        pm.set(body.key, body.value)
        return {"ok": True, "profile": pm.profile_summary()}

    @app.get("/api/wings")
    def wings() -> Dict[str, Any]:
        from superai.core.wings import WingsManager

        return WingsManager().list_wings()

    @app.get("/api/learnings/summary")
    def learnings_summary() -> Dict[str, Any]:
        from superai.core.learning_engine import LearningEngine
        from superai.core.memory_palace import MemoryPalace

        return LearningEngine(MemoryPalace()).get_learnings_summary()

    @app.get("/charts", response_class=HTMLResponse)
    def charts_home() -> str:
        return """<!doctype html>
<html><head><meta charset="utf-8"><title>SuperAI Charts</title>
<style>
 body{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem}
 textarea{width:100%;min-height:180px;font-family:ui-monospace,monospace}
 button{font-size:1rem;padding:.5rem 1rem;margin-top:.5rem}
 #frame{width:100%;min-height:420px;border:1px solid #ccc;border-radius:8px;margin-top:1rem}
</style></head>
<body>
<h1>Interactive Vega charts</h1>
<p>Paste a Vega-Lite JSON spec (from <code>superai data-ask --chart</code>) and render.</p>
<textarea id="spec" placeholder='{"$schema":"https://vega.github.io/schema/vega-lite/v5.json",...}'></textarea>
<br/><button onclick="render()">Render</button>
<iframe id="frame" title="chart"></iframe>
<script>
async function render(){
  let spec;
  try { spec = JSON.parse(document.getElementById('spec').value); }
  catch(e){ alert('Invalid JSON: '+e); return; }
  const r = await fetch('/api/charts/render', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({spec: spec, title:'SuperAI Chart'})
  });
  const html = await r.text();
  const frame = document.getElementById('frame');
  frame.srcdoc = html;
}
</script>
</body></html>"""

    @app.post("/api/charts/render", response_class=HTMLResponse)
    async def render_chart(request: Request) -> str:
        """Accept raw JSON body: {spec: {...}, title?: str}."""
        from superai.core.vega_charts import render_vega_html

        try:
            payload = await request.json()
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}") from e
        if not isinstance(payload, dict) or "spec" not in payload:
            raise HTTPException(status_code=400, detail="Body must include 'spec'")
        spec = payload["spec"]
        title = str(payload.get("title") or "SuperAI Chart")
        if not isinstance(spec, dict):
            raise HTTPException(status_code=400, detail="'spec' must be an object")
        try:
            return render_vega_html(spec, title=title)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(e)) from e

    @app.get("/api/plugins")
    def list_plugins(q: Optional[str] = None) -> Dict[str, Any]:
        from superai.core.plugin_registry import PluginRegistry

        reg = PluginRegistry()
        plugins = reg.search(q) if q else reg.list_plugins()
        return {"summary": reg.marketplace_summary(), "plugins": plugins}

    @app.get("/api/bandit")
    def bandit_state() -> Dict[str, Any]:
        from superai.core.bandit_router import EpsilonGreedyBandit

        b = EpsilonGreedyBandit()
        return {"epsilon": b.epsilon, "arms": b.state, "path": str(b.path)}

    return app


# ASGI entry for uvicorn superai.web_app:app
if HAS_FASTAPI:
    app = create_app()
else:
    app = None  # type: ignore
