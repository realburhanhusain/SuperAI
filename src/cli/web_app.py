"""
Minimal FastAPI web surface for SuperAI (memory query + status).

Run:
  pip install -e ".[web]"
  superai web
  # or: uvicorn scli.web_app:app --reload --port 8787
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from pathlib import Path

try:
    from fastapi import FastAPI, HTTPException, Query, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel, Field

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    FastAPI = object  # type: ignore
    BaseModel = object  # type: ignore
    Request = object  # type: ignore
    StaticFiles = object  # type: ignore


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

    # N13: PWA static shell
    pwa_dir = Path(__file__).resolve().parent / "static" / "pwa"
    if pwa_dir.is_dir():
        app.mount("/pwa", StaticFiles(directory=str(pwa_dir), html=True), name="pwa")

    def _check_auth(request: Request) -> None:
        """Optional bearer auth via SUPERAI_WEB_TOKEN (required if set)."""
        token = (os.getenv("SUPERAI_WEB_TOKEN") or "").strip()
        if not token:
            return
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            got = auth[7:].strip()
        else:
            got = request.headers.get("x-superai-token") or ""
        if got != token:
            raise HTTPException(status_code=401, detail="Unauthorized")

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        # Allow static HTML shells without token; protect /api/*
        if request.url.path.startswith("/api/"):
            _check_auth(request)
        return await call_next(request)

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
<p>Shared surface for terminal + web (Mempalace-inspired).
 <a href="/dashboard">Dashboard</a> · <a href="/cli-pool">CLI Pool</a> ·
 <a href="/charts">Charts</a> · <a href="/pwa/">PWA</a></p>
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
  const esc=s=>String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  (j.results||[]).forEach(m=>{
    html+='<div class="card"><b>'+esc(m.id||'')+'</b><br/>'+
      esc((m.content||'').slice(0,400))+'<br/><small>'+
      esc(JSON.stringify(m.metadata||{}))+'</small></div>';
  });
  document.getElementById('out').innerHTML=html||esc(JSON.stringify(j,null,2));
}
async function status(){
  const r=await fetch('/api/status');
  document.getElementById('out').textContent=JSON.stringify(await r.json(),null,2);
}
</script>
</body></html>"""

    @app.get("/api/status")
    def api_status() -> Dict[str, Any]:
        from core import __version__
        from core.config import Config
        from core.history import TaskHistory
        from core.memory_palace import MemoryPalace
        from core.preferences import UserPreferenceModel

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
        from core.memory_palace import MemoryPalace

        tag_list = [t.strip() for t in tags.split(",")] if tags else None
        mp = MemoryPalace()
        results = mp.query_semantic(q, top_k=top_k, tags=tag_list)
        return {"query": q, "count": len(results), "results": results}

    @app.post("/api/memory/search")
    def memory_search_post(body: MemoryQuery) -> Dict[str, Any]:
        return memory_search(body.query, body.top_k, body.tags)

    @app.get("/api/preferences")
    def get_prefs() -> Dict[str, Any]:
        from core.preferences import UserPreferenceModel

        return UserPreferenceModel().profile_summary()

    @app.post("/api/preferences")
    def set_pref(body: PreferenceBody) -> Dict[str, Any]:
        from core.preferences import UserPreferenceModel

        pm = UserPreferenceModel()
        pm.set(body.key, body.value)
        return {"ok": True, "profile": pm.profile_summary()}

    @app.get("/api/wings")
    def wings() -> Dict[str, Any]:
        from core.wings import WingsManager

        return WingsManager().list_wings()

    @app.get("/api/learnings/summary")
    def learnings_summary() -> Dict[str, Any]:
        from core.learning_engine import LearningEngine
        from core.memory_palace import MemoryPalace

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
        from core.vega_charts import render_vega_html

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
        from core.plugin_registry import PluginRegistry

        reg = PluginRegistry()
        plugins = reg.search(q) if q else reg.list_plugins()
        return {"summary": reg.marketplace_summary(), "plugins": plugins}

    @app.get("/api/bandit")
    def bandit_state() -> Dict[str, Any]:
        from core.bandit_router import EpsilonGreedyBandit

        b = EpsilonGreedyBandit()
        return {"epsilon": b.epsilon, "arms": b.state, "path": str(b.path)}

    @app.get("/api/dashboard")
    def api_dashboard() -> Dict[str, Any]:
        from core.observability import (
            build_dashboard_snapshot,
            recent_feedback,
        )

        snap = build_dashboard_snapshot()
        snap["feedback"] = recent_feedback(10)
        return snap

    class FeedbackBody(BaseModel):
        message: str
        surface: str = "web"
        task_id: Optional[str] = None

    @app.post("/api/feedback")
    def api_feedback(body: FeedbackBody) -> Dict[str, Any]:
        from core.observability import write_feedback, recent_feedback

        entry = write_feedback(body.message, surface=body.surface, task_id=body.task_id)
        return {"ok": True, "entry": entry, "recent": recent_feedback(5)}

    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard_page() -> str:
        return """<!doctype html>
<html><head><meta charset="utf-8"><title>SuperAI Dashboard</title>
<style>
 body{font-family:system-ui,sans-serif;max-width:1000px;margin:1.5rem auto;padding:0 1rem}
 .grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
 .card{border:1px solid #ddd;border-radius:10px;padding:.75rem;background:#fafbfc}
 pre{white-space:pre-wrap;font-size:.85rem;max-height:280px;overflow:auto}
 h1{font-size:1.3rem}
</style></head>
<body>
<h1>SuperAI Dashboard</h1>
<p><a href="/">Memory</a> · <a href="/charts">Charts</a> ·
<button onclick="load()">Refresh</button></p>
<div class="grid">
 <div class="card"><h3>Snapshot</h3><pre id="snap">…</pre></div>
 <div class="card"><h3>Feedback</h3>
  <input id="fb" size="40" placeholder="Cross-surface feedback"/>
  <button onclick="sendFb()">Send</button>
  <pre id="fblist"></pre>
 </div>
</div>
<script>
async function load(){
  const r=await fetch('/api/dashboard');
  const j=await r.json();
  document.getElementById('snap').textContent=JSON.stringify(j,null,2);
  document.getElementById('fblist').textContent=JSON.stringify(j.feedback||[],null,2);
}
async function sendFb(){
  const message=document.getElementById('fb').value;
  await fetch('/api/feedback',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({message,surface:'web'})});
  load();
}
load();
setInterval(load, 8000);
</script>
</body></html>"""

    @app.get("/api/ecosystem")
    def api_ecosystem() -> Dict[str, Any]:
        from core.ecosystem import EcosystemHub

        return EcosystemHub().capabilities()

    @app.get("/api/cli-pool")
    def api_cli_pool(
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """All parallel CLI workers for agentic multi-CLI dashboard."""
        from core.cli_pool import ParallelCLIManager

        mgr = ParallelCLIManager()
        return {
            "snapshot": mgr.snapshot_for_dashboard(),
            "jobs": mgr.list_jobs(status=status, workflow_id=workflow_id, limit=80),
        }

    @app.get("/cli-pool", response_class=HTMLResponse)
    def cli_pool_page() -> str:
        return """<!doctype html>
<html><head><meta charset="utf-8"><title>SuperAI CLI Pool</title>
<style>
 body{font-family:system-ui,sans-serif;max-width:1100px;margin:1.5rem auto;padding:0 1rem}
 table{border-collapse:collapse;width:100%;font-size:.9rem}
 th,td{border:1px solid #ddd;padding:.4rem .5rem;text-align:left}
 th{background:#f0f4f8}
 .running{background:#fff8e1}.done{background:#e8f5e9}.failed{background:#ffebee}
 #meta{opacity:.7;margin-bottom:1rem}
</style></head>
<body>
<h1>Parallel CLI workers</h1>
<p id="meta">Loading… · <a href="/">Home</a> · <a href="/dashboard">Dashboard</a></p>
<table>
 <thead><tr>
  <th>Job</th><th>CLI</th><th>Role</th><th>Status</th><th>Sec</th>
  <th>Workflow</th><th>Output</th>
 </tr></thead>
 <tbody id="rows"></tbody>
</table>
<script>
async function load(){
  const r=await fetch('/api/cli-pool');
  const j=await r.json();
  const s=j.snapshot||{};
  const t=s.totals||{};
  document.getElementById('meta').textContent=
    `running=${t.running||0} queued=${t.queued||0} done=${t.done||0} failed=${t.failed||0} · auto-refresh 2s`;
  const jobs=j.jobs||[];
  const tb=document.getElementById('rows');
  tb.innerHTML='';
  jobs.forEach(job=>{
    const tr=document.createElement('tr');
    tr.className=job.status||'';
    const out=(job.stdout_tail||job.error||'').slice(0,80).replace(/</g,'&lt;');
    tr.innerHTML=`<td>${job.id||''}</td><td>${job.cli||''}</td><td>${job.role||''}</td>
      <td>${job.status||''}</td><td>${job.duration_sec||0}</td>
      <td>${job.workflow_id||''}</td><td><code>${out}</code></td>`;
    tb.appendChild(tr);
  });
  if(!jobs.length){
    tb.innerHTML='<tr><td colspan="7">No CLI jobs. Run: superai cli-parallel "task" --dry-run</td></tr>';
  }
}
load();
setInterval(load, 2000);
</script>
</body></html>"""

    # S22: WebSocket live dashboard events (broadcast simple snapshots)
    try:
        from fastapi import WebSocket, WebSocketDisconnect

        @app.websocket("/ws/dashboard")
        async def ws_dashboard(websocket: WebSocket) -> None:
            await websocket.accept()
            import asyncio

            try:
                while True:
                    from core.observability import build_dashboard_snapshot

                    snap = build_dashboard_snapshot(history_limit=5, log_lines=5)
                    await websocket.send_json(snap)
                    await asyncio.sleep(3)
            except WebSocketDisconnect:
                return
            except Exception:
                try:
                    await websocket.close()
                except Exception:
                    pass
    except Exception:
        pass

    return app


# ASGI entry for uvicorn scli.web_app:app
if HAS_FASTAPI:
    app = create_app()
else:
    app = None  # type: ignore
