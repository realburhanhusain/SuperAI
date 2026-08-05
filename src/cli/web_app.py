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
    from fastapi import FastAPI, HTTPException, Query, Request, Response
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

    enable_config_write = os.getenv("SUPERAI_WEB_ENABLE_CONFIG_WRITE") == "1"
    management_token = (os.getenv("SUPERAI_WEB_MANAGEMENT_TOKEN") or "").strip()

    app = FastAPI(
        title="SuperAI Web",
        version="0.1.0",
        description="Memory query + status API for SuperAI",
    )

    # N13: PWA static shell
    pwa_dir = Path(__file__).resolve().parent / "static" / "pwa"
    if pwa_dir.is_dir():
        app.mount("/pwa", StaticFiles(directory=str(pwa_dir), html=True), name="pwa")

    def _client_is_loopback(request: Request) -> bool:
        host = (request.client.host if request.client else "") or ""
        return host in {"127.0.0.1", "::1", "localhost", "testclient"}

    def _check_auth(request: Request) -> None:
        """
        Web API auth (V6 M094):
        - SUPERAI_WEB_TOKEN required for non-loopback API access
        - Loopback may run without token for local dev
        - When token set, always required for /api/*
        """
        token = (os.getenv("SUPERAI_WEB_TOKEN") or "").strip()
        require = bool(token) or not _client_is_loopback(request)
        # Allow loopback without token only when SUPERAI_WEB_TOKEN unset
        if not token and _client_is_loopback(request):
            return
        if not token and require:
            raise HTTPException(
                status_code=401,
                detail="SUPERAI_WEB_TOKEN required for non-loopback API access",
            )
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            got = auth[7:].strip()
        else:
            got = request.headers.get("x-superai-token") or ""
        if token and got != token:
            raise HTTPException(status_code=401, detail="Unauthorized")
        if not token and not _client_is_loopback(request):
            raise HTTPException(status_code=401, detail="Unauthorized")

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        # Allow static HTML shells without token; protect /api/*
        if request.url.path.startswith("/api/"):
            _check_auth(request)
        return await call_next(request)

    @app.middleware("http")
    async def contract_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        """
        V4-M2/V3-A4: every JSON response under ``/api/*`` carries the contract.

        One seam rather than editing 20 handlers, matching how the CLI does it
        (``public_surface.contract_console``). Applied at the response layer so
        a route added tomorrow is contracted without anyone remembering to.

        Deliberately narrow:

        - Only ``/api/*``. ``POST /mcp`` is JSON-RPC, whose envelope is fixed by
          the MCP spec and contracted one layer in by ``wrap_mcp_tool``.
        - Only ``application/json``. HTML pages and ``/api/charts/render``
          (an ``HTMLResponse``) pass through untouched.
        - Only top-level JSON objects. A bare array is not an envelope, and
          wrapping it here would change the response type behind the caller's
          back; those routes are fixed individually.
        """
        response = await call_next(request)
        if not request.url.path.startswith("/api/"):
            return response
        if "application/json" not in (response.headers.get("content-type") or ""):
            return response
        body = b""
        async for chunk in response.body_iterator:  # type: ignore[attr-defined]
            body += chunk
        try:
            import json as _json

            from core.public_surface import contract_payload

            payload = _json.loads(body.decode("utf-8"))
            if isinstance(payload, dict):
                payload = contract_payload(payload, ok=response.status_code < 400)
                body = _json.dumps(payload, default=str).encode("utf-8")
        except Exception:
            # A body we cannot parse is returned exactly as produced. Never
            # swallow a real response to satisfy a contract check.
            pass
        headers = dict(response.headers)
        headers.pop("content-length", None)
        return Response(
            content=body,
            status_code=response.status_code,
            headers=headers,
            media_type="application/json",
        )

    if enable_config_write:
        if not management_token:
            import logging
            logging.getLogger("superai.web_app").error("SUPERAI_WEB_ENABLE_CONFIG_WRITE is on but SUPERAI_WEB_MANAGEMENT_TOKEN is unset. Write routes will NOT be enabled.")
        else:
            def _check_management_auth(req: Request) -> None:
                """
                Management token required unconditionally (including loopback).
                Header-bearer auth is CSRF-safe by construction: a foreign page cannot attach
                the Authorization header without already holding the token. This holds only
                while the token is never stored in a cookie.
                """
                auth = req.headers.get("authorization") or ""
                if auth.lower().startswith("bearer "):
                    got = auth[7:].strip()
                else:
                    got = req.headers.get("x-superai-management-token") or ""
                
                if not got:
                    raise HTTPException(status_code=401, detail="Management token required")
                
                import hmac
                if not hmac.compare_digest(got.encode('utf-8'), management_token.encode('utf-8')):
                    raise HTTPException(status_code=401, detail="Unauthorized management token")

            @app.get("/api/config")
            async def get_config(request: Request) -> Dict[str, Any]:
                _check_management_auth(request)
                from core.config import Config
                from core.secrets import redact_obj
                cfg = Config().show()
                return {"ok": True, "config": redact_obj(cfg)}

            @app.post("/api/config")
            async def update_config(request: Request) -> Dict[str, Any]:
                _check_management_auth(request)
                payload = await request.json()
                changes = payload.get("changes", {})
                
                from core.config import validate_changes, Config, diff_changes
                from core.audit_log import AuditLog
                from core.secrets import redact_obj
                import urllib.parse
                
                errors = validate_changes(changes)
                if errors:
                    AuditLog().record("config.write", detail={"changes": redact_obj(changes), "errors": errors}, actor="web", outcome="failure")
                    raise HTTPException(status_code=400, detail={"errors": errors})
                
                cfg = Config()
                
                # Apply changes and save
                for k, v in changes.items():
                    cfg.set(k, v, persist=False)
                
                cfg.save()
                
                # Check latest backup
                backup_id = None
                backups_dir = cfg.home_dir / "backups"
                if backups_dir.exists():
                    backups = sorted(backups_dir.glob("config-*.json"))
                    if backups:
                        backup_id = backups[-1].name
                
                AuditLog().record("config.write", detail={"changes": redact_obj(changes), "backup": backup_id}, actor="web", outcome="success")
                
                return {
                    "ok": True,
                    "status": "updated",
                    "backup_id": backup_id,
                    "changes": changes,
                    "hot_reload": "Some settings may require a restart to take effect (e.g. settings imported at module load time)."
                }


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
 <a href="/terminals">Terminals</a> · <a href="/palace">Palace</a> ·
 <a href="/mcp">MCP</a> ·
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
        from core.palace_tenant import current_tenant
        from core.preferences import UserPreferenceModel
        from core.result_contract import apply_contract

        cfg = Config()
        mp = MemoryPalace()
        payload: Dict[str, Any] = {
            "ok": True,
            "status": "success",
            "version": __version__,
            "mock_mode": cfg.use_mock,
            "mock": bool(cfg.use_mock),
            "dry_run": False,
            "tenant_id": current_tenant(cfg),
            "history": TaskHistory().count(),
            "memory": mp.get_memory_stats(),
            "preferences": UserPreferenceModel().profile_summary(),
        }
        return apply_contract(payload, mock=bool(cfg.use_mock), dry_run=False, ok=True)

    @app.get("/api/cliproxy/status")
    def api_cliproxy_status() -> Dict[str, Any]:
        from core.provider_catalog import OPENAI_COMPAT_PROVIDERS
        from core.smoke_preflight import check_local_up

        cfg = OPENAI_COMPAT_PROVIDERS.get("cliproxy", {})
        base_url = cfg.get("base_url", "http://127.0.0.1:8317/v1")
        
        reachable = check_local_up("cliproxy", timeout=2.0)
        
        return {
            "configured_base_url": base_url,
            "reachable": reachable,
        }

    @app.get("/api/agent-graph")
    def api_agent_graph(
        task_id: Optional[str] = Query(None),
    ) -> Dict[str, Any]:
        """Phase 8 N4: subagent/run graph for dashboard."""
        from core.agent_graph import graph_from_adaptation_events, graph_from_run_result
        from core.history import TaskHistory

        result = {}
        if task_id:
            try:
                # best-effort load last result from history
                hist = TaskHistory()
                if hasattr(hist, "get"):
                    result = hist.get(task_id) or {}
                elif hasattr(hist, "load"):
                    result = hist.load(task_id) or {}
            except Exception:
                result = {}
        events = (result.get("metadata") or {}).get("adaptation_events") or []
        if events:
            return graph_from_adaptation_events(events)
        return graph_from_run_result(result)

    # SuperAI agent HTTP surface (multi-agent tool loop)
    @app.get("/api/superai/roles")
    def api_superai_roles() -> Dict[str, Any]:
        from core.superai_agent.agents import list_agents

        return {"ok": True, "agents": list_agents()}

    @app.get("/api/superai/sessions")
    def api_superai_sessions(limit: int = Query(20, ge=1, le=100)) -> Dict[str, Any]:
        from core.superai_agent.session import SuperAISessionStore

        return {"ok": True, "sessions": SuperAISessionStore().list_sessions(limit)}

    @app.post("/api/superai/run")
    async def api_superai_run(request: Request) -> Dict[str, Any]:
        """
        One-shot SuperAI agent run (safe defaults: mock + plan permission).
        Body: {prompt, agent?, model?, session_id?, permission?, live?}
        """
        from core.superai_agent.runtime import AgentRuntime

        try:
            body = await request.json()
        except Exception:
            body = {}
        if not isinstance(body, dict):
            body = {}
        prompt = str(body.get("prompt") or body.get("task") or "").strip()
        if not prompt:
            raise HTTPException(status_code=400, detail="prompt required")
        live = bool(body.get("live"))
        import os

        if live and (os.getenv("SUPERAI_MCP_ALLOW_LIVE") or "").lower() not in {
            "1",
            "true",
            "yes",
        }:
            from core.spend_guard import ensure_public_result

            return ensure_public_result(
                {
                    "ok": False,
                    "error": "live requires SUPERAI_MCP_ALLOW_LIVE=1",
                    "mock": True,
                },
                mock=True,
                ok=False,
            )
        # DoD-strict budget gate on every HTTP agent run (mock or live)
        try:
            from core.spend_guard import budget_precheck, ensure_public_result

            block = budget_precheck(
                estimated_usd=0.15 if live else 0.0,
                tokens=800 if live else 50,
                command_name="web",
                enforce=False if not live else None,
            )
            if block.get("blocked") or block.get("ok") is False:
                return ensure_public_result(block, mock=not live, ok=False)
        except Exception as e:
            import logging

            logging.getLogger("superai.web_app").warning(
                "budget gate check failed: %s", e,
            )
            # Fail closed for live spend paths
            if live:
                from core.spend_guard import ensure_public_result

                return ensure_public_result(
                    {
                        "ok": False,
                        "blocked": True,
                        "error": f"budget gate failure: {e}",
                        "error_code": "budget_internal",
                    },
                    mock=False,
                    ok=False,
                )
        rt = AgentRuntime(use_mock=not live)
        out = rt.run(
            prompt,
            session_id=body.get("session_id"),
            agent=str(body.get("agent") or "build"),
            model=body.get("model"),
            permission=str(body.get("permission") or ("ask" if live else "plan")),
        )
        data = out.to_dict()
        try:
            from core.spend_guard import budget_record, ensure_public_result

            budget_record(
                usd=float(data.get("estimated_cost_usd") or 0),
                tokens=int(data.get("tokens") or 0),
            )
            return ensure_public_result(
                data,
                mock=bool(data.get("mock", not live)),
                ok=bool(data.get("ok", True)),
            )
        except Exception:
            return data

    @app.get("/graph")
    def graph_page(task_id: Optional[str] = None):
        """V3 C: SVG graph visualizer from /api/agent-graph."""
        from fastapi import Response
        from core.agent_graph import graph_from_adaptation_events, graph_from_run_result, generate_svg
        from core.history import TaskHistory

        result = {}
        if task_id:
            try:
                hist = TaskHistory()
                if hasattr(hist, "get"):
                    result = hist.get(task_id) or {}
                elif hasattr(hist, "load"):
                    result = hist.load(task_id) or {}
            except Exception:
                result = {}
        events = (result.get("metadata") or {}).get("adaptation_events") or []
        if events:
            graph = graph_from_adaptation_events(events)
        else:
            graph = graph_from_run_result(result)

        return Response(content=generate_svg(graph), media_type="image/svg+xml")

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

    @app.get("/api/palace")
    def api_palace(
        wing: Optional[str] = None,
        room: Optional[str] = None,
        limit: int = Query(12, ge=1, le=50),
    ) -> Dict[str, Any]:
        """Memory Palace browser snapshot (layout, clusters, suggestions)."""
        from core.memory_palace import MemoryPalace

        return MemoryPalace().browser_snapshot(wing=wing, room=room, limit=limit)

    @app.get("/api/palace/suggest")
    def api_palace_suggest(
        min_size: int = Query(3, ge=1, le=50),
        method: str = Query("auto"),
    ) -> Dict[str, Any]:
        from core.memory_palace import MemoryPalace

        return {
            "suggestions": MemoryPalace().suggest_rooms_from_clusters(
                min_size=min_size, method=method
            )
        }

    @app.post("/api/palace/promote")
    def api_palace_promote(
        apply: bool = Query(False),
        reassign: bool = Query(False),
        min_size: int = Query(3, ge=1, le=50),
    ) -> Dict[str, Any]:
        from core.memory_palace import MemoryPalace

        return MemoryPalace().auto_promote_rooms(
            apply=apply, reassign=reassign, min_size=min_size
        )

    @app.get("/palace", response_class=HTMLResponse)
    def palace_page() -> str:
        return """<!doctype html>
<html><head><meta charset="utf-8"><title>SuperAI Memory Palace</title>
<style>
 body{font-family:system-ui,sans-serif;max-width:1100px;margin:1.5rem auto;padding:0 1rem}
 .grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
 .card{border:1px solid #ddd;border-radius:8px;padding:.75rem}
 table{border-collapse:collapse;width:100%;font-size:.9rem}
 th,td{border:1px solid #eee;padding:.35rem .5rem;text-align:left}
 th{background:#f4f7fb}
 #meta{opacity:.75;margin-bottom:1rem}
 @media(max-width:800px){.grid{grid-template-columns:1fr}}
</style></head>
<body>
<h1>Memory Palace browser</h1>
<p id="meta">Loading… · <a href="/">Home</a> · <a href="/dashboard">Dashboard</a></p>
<div class="grid">
 <div class="card"><h2>Wings</h2><table><thead><tr><th>Wing</th><th>Count</th></tr></thead><tbody id="wings"></tbody></table></div>
 <div class="card"><h2>Room suggestions</h2><table><thead><tr><th>Wing/Room</th><th>Size</th><th>New?</th></tr></thead><tbody id="sug"></tbody></table>
  <button onclick="promote()">Promote new rooms (apply)</button></div>
 <div class="card" style="grid-column:1/-1"><h2>Browse</h2>
  <label>Wing <input id="wing" placeholder="technical"/></label>
  <label>Room <input id="room" placeholder="coding"/></label>
  <button onclick="load()">Refresh</button>
  <table><thead><tr><th>ID</th><th>Wing</th><th>Room</th><th>Content</th></tr></thead><tbody id="items"></tbody></table>
 </div>
</div>
<script>
async function load(){
  const w=document.getElementById('wing').value;
  const r=document.getElementById('room').value;
  const u='/api/palace?limit=15'+(w?'&wing='+encodeURIComponent(w):'')+(r?'&room='+encodeURIComponent(r):'');
  const j=await (await fetch(u)).json();
  const L=j.layout||{};
  document.getElementById('meta').textContent=
    'located='+(L.total_located||0)+' unassigned='+(L.unassigned||0)+' · auto-refresh 5s';
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const wb=document.getElementById('wings'); wb.innerHTML='';
  (j.top_wings||[]).forEach(row=>{
    const tr=document.createElement('tr');
    tr.innerHTML='<td>'+esc(row.wing)+'</td><td>'+esc(row.count)+'</td>';
    wb.appendChild(tr);
  });
  const sb=document.getElementById('sug'); sb.innerHTML='';
  (j.suggestions||[]).forEach(s=>{
    const tr=document.createElement('tr');
    tr.innerHTML='<td>'+esc(s.wing)+'/'+esc(s.room)+'</td><td>'+esc(s.size)+'</td><td>'+esc(s.already_in_catalog?'no':'YES')+'</td>';
    sb.appendChild(tr);
  });
  const ib=document.getElementById('items'); ib.innerHTML='';
  ((j.browse||{}).items||[]).forEach(m=>{
    const tr=document.createElement('tr');
    tr.innerHTML='<td>'+esc(m.id)+'</td><td>'+esc(m.wing)+'</td><td>'+esc(m.room)+'</td><td>'+esc((m.content||'').slice(0,200))+'</td>';
    ib.appendChild(tr);
  });
}
async function promote(){
  const j=await (await fetch('/api/palace/promote?apply=true',{method:'POST'})).json();
  alert('Promoted '+((j.promoted_count)||0)+' room(s)');
  load();
}
load();
setInterval(load, 5000);
</script>
</body></html>"""

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


    @app.get("/api/goals")
    def api_goals() -> Dict[str, Any]:
        from core.goals_daemon import status

        return status()

    @app.get("/api/spend")
    def api_spend() -> Dict[str, Any]:
        from core.cost_accounting import aggregate_costs
        from core.history import TaskHistory

        parts = TaskHistory().list(limit=5000)
        total = aggregate_costs(parts)

        breakdown = {}
        for p in parts:
            if not isinstance(p, dict):
                continue
            model = str(p.get("model") or p.get("member") or "unknown")
            if model not in breakdown:
                breakdown[model] = []
            breakdown[model].append(p)
            
        total["by_model"] = {
            m: aggregate_costs(m_parts)
            for m, m_parts in breakdown.items()
        }
        return total


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

    @app.post("/mcp")
    async def mcp_http(request: Request) -> Any:
        """
        Local MCP over HTTP (JSON-RPC).
        Other AIs / automation can POST initialize | tools/list | tools/call.
        Auth: SUPERAI_WEB_TOKEN if set (Bearer / x-superai-token).
        """
        _check_auth(request)
        from core.mcp_server import handle_request

        try:
            body = await request.json()
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"invalid JSON: {e}") from e
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="JSON object required")
        return handle_request(body)

    @app.get("/api/mcp/tools")
    def api_mcp_tools() -> Dict[str, Any]:
        from core.mcp_server import list_tools, client_config_snippet

        return {
            "tools": list_tools(),
            "stdio": "superai mcp-serve",
            "http": "POST /mcp",
            "client_config": client_config_snippet(),
        }

    @app.get("/mcp", response_class=HTMLResponse)
    def mcp_page() -> str:
        return """<!doctype html>
<html><head><meta charset="utf-8"><title>SuperAI MCP</title>
<style>
 body{font-family:system-ui,sans-serif;max-width:900px;margin:1.5rem auto;padding:0 1rem}
 code,pre{background:#f4f6f8;padding:.2rem .4rem;border-radius:4px}
 pre{padding:1rem;overflow:auto}
 li{margin:.35rem 0}
</style></head>
<body>
<h1>SuperAI local MCP</h1>
<p><a href="/">Home</a> · Other AIs connect here to share <b>central Memory Palace</b>
 and run CLIs through SuperAI.</p>
<h2>stdio (Claude Desktop / Cursor)</h2>
<pre>superai mcp-config
superai mcp-serve</pre>
<p>Merge <code>mcpServers.superai</code> from <code>superai mcp-config</code> into the client.</p>
<h2>HTTP</h2>
<pre>POST /mcp  (JSON-RPC: initialize | tools/list | tools/call)
GET  /api/mcp/tools</pre>
<ul id="tools"><li>Loading…</li></ul>
<script>
fetch('/api/mcp/tools').then(r=>r.json()).then(j=>{
  const ul=document.getElementById('tools');
  ul.innerHTML='';
  (j.tools||[]).forEach(t=>{
    const li=document.createElement('li');
    li.innerHTML='<code>'+t.name+'</code> — '+(t.description||'');
    ul.appendChild(li);
  });
});
</script>
</body></html>"""

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
<p id="meta">Loading… · <a href="/">Home</a> · <a href="/dashboard">Dashboard</a> · <a href="/terminals">Terminals</a></p>
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
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const jobs=j.jobs||[];
  const tb=document.getElementById('rows');
  tb.innerHTML='';
  jobs.forEach(job=>{
    const tr=document.createElement('tr');
    tr.className=esc(job.status||'');
    const out=esc((job.stdout_tail||job.error||'').slice(0,80));
    tr.innerHTML=`<td>${esc(job.id)}</td><td>${esc(job.cli)}</td><td>${esc(job.role)}</td>
      <td>${esc(job.status)}</td><td>${esc(job.duration_sec||0)}</td>
      <td>${esc(job.workflow_id)}</td><td><code>${out}</code></td>`;
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

    @app.get("/api/terminals")
    def api_terminals(
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """All parallel terminal sessions for agentic multi-terminal dashboard."""
        from core.terminal_pool import ParallelTerminalManager

        mgr = ParallelTerminalManager()
        return {
            "snapshot": mgr.snapshot_for_dashboard(),
            "sessions": mgr.list_sessions(
                status=status, workflow_id=workflow_id, limit=80
            ),
        }

    @app.get("/terminals", response_class=HTMLResponse)
    def terminals_page() -> str:
        return """<!doctype html>
<html><head><meta charset="utf-8"><title>SuperAI Terminals</title>
<style>
 body{font-family:system-ui,sans-serif;max-width:1200px;margin:1.5rem auto;padding:0 1rem}
 table{border-collapse:collapse;width:100%;font-size:.9rem}
 th,td{border:1px solid #ddd;padding:.4rem .5rem;text-align:left;vertical-align:top}
 th{background:#e8f4fc}
 .running{background:#fff8e1}.done{background:#e8f5e9}.failed{background:#ffebee}
 #meta{opacity:.7;margin-bottom:1rem}
 code{font-size:.8rem;word-break:break-all}
</style></head>
<body>
<h1>Parallel terminals</h1>
<p id="meta">Loading… · <a href="/">Home</a> · <a href="/dashboard">Dashboard</a> · <a href="/cli-pool">CLI pool</a></p>
<table>
 <thead><tr>
  <th>Session</th><th>Title</th><th>Role</th><th>Status</th><th>Sec</th>
  <th>Workflow</th><th>Command</th><th>Output</th>
 </tr></thead>
 <tbody id="rows"></tbody>
</table>
<script>
async function load(){
  const r=await fetch('/api/terminals');
  const j=await r.json();
  const s=j.snapshot||{};
  const t=s.totals||{};
  document.getElementById('meta').textContent=
    `running=${t.running||0} queued=${t.queued||0} done=${t.done||0} failed=${t.failed||0} · auto-refresh 2s`;
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const sessions=j.sessions||[];
  const tb=document.getElementById('rows');
  tb.innerHTML='';
  sessions.forEach(sess=>{
    const tr=document.createElement('tr');
    tr.className=esc(sess.status||'');
    const out=esc((sess.stdout_tail||sess.error||'').slice(0,100));
    const cmd=esc((sess.command||[]).join(' ').slice(0,80));
    tr.innerHTML=`<td>${esc(sess.id)}</td><td>${esc(sess.title)}</td><td>${esc(sess.role)}</td>
      <td>${esc(sess.status)}</td><td>${esc(sess.duration_sec||0)}</td>
      <td>${esc(sess.workflow_id)}</td><td><code>${cmd}</code></td>
      <td><code>${out}</code></td>`;
    tb.appendChild(tr);
  });
  if(!sessions.length){
    tb.innerHTML='<tr><td colspan="8">No terminals. Run: superai term-parallel "task" --dry-run</td></tr>';
  }
}
load();
setInterval(load, 2000);
</script>
</body></html>"""

    @app.get("/console", response_class=HTMLResponse)
    def console_page() -> str:
        return """<!doctype html>
<html><head><meta charset="utf-8"><title>SuperAI Console</title>
<style>
 body{font-family:system-ui,sans-serif;max-width:1200px;margin:1.5rem auto;padding:0 1rem}
 .grid{display:grid;grid-template-columns:repeat(auto-fit, minmax(350px, 1fr));gap:1rem}
 .card{border:1px solid #ddd;border-radius:10px;padding:.75rem;background:#fafbfc}
 pre{white-space:pre-wrap;font-size:.85rem;max-height:280px;overflow:auto}
 h1,h2{margin-top:0}
 .signals{background:#e8f4fc;padding:1rem;border-radius:10px;margin-bottom:1rem;display:flex;gap:1.5rem;align-items:center}
 .signal-pill{background:#fff;padding:.25rem .75rem;border-radius:20px;border:1px solid #ccc;font-weight:600}
 .mock{color:#d32f2f;border-color:#d32f2f;background:#ffebee}
 .live{color:#2e7d32;border-color:#2e7d32;background:#e8f5e9}
 #cliproxy-link{margin-left:auto;text-decoration:none;background:#2196f3;color:#fff;padding:.5rem 1rem;border-radius:4px;font-weight:bold}
 .error{color:#d32f2f}
</style></head>
<body>
<h1>SuperAI Console</h1>
<div class="signals">
  <div><strong>Signals:</strong></div>
  <div id="sig-mode" class="signal-pill">Loading mode...</div>
  <div id="sig-cost" class="signal-pill">Loading cost basis...</div>
  <a id="cliproxy-link" href="/cliproxy-admin">Manage Proxy (CLIProxyAPI)</a>
</div>
<div class="grid">
  <div class="card"><h2>Dashboard</h2><pre id="p-dashboard">Loading...</pre></div>
  <div class="card"><h2>Bandit Router</h2><pre id="p-bandit">Loading...</pre></div>
  <div class="card"><h2>CLI Pool</h2><pre id="p-clipool">Loading...</pre></div>
  <div class="card"><h2>Learnings</h2><pre id="p-learnings">Loading...</pre></div>
  <div class="card"><h2>Spend (Cost)</h2><pre id="p-spend">Loading...</pre></div>
  <div class="card"><h2>Goals Daemon</h2><pre id="p-goals">Loading...</pre></div>
  <div class="card"><h2>CLIProxy Status</h2><pre id="p-cliproxy">Loading...</pre></div>
</div>
<script>
const token = sessionStorage.getItem('SUPERAI_WEB_TOKEN') || sessionStorage.getItem('SUPERAI_WEB_MANAGEMENT_TOKEN');
const headers = token ? { 'Authorization': 'Bearer ' + token } : {};

async function fetchPanel(url, id, onData) {
  try {
    const res = await fetch(url, { headers });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    document.getElementById(id).textContent = JSON.stringify(data, null, 2);
    if (onData) onData(data);
  } catch(e) {
    document.getElementById(id).textContent = 'Failed: ' + e.message;
    document.getElementById(id).className = 'error';
  }
}

function loadAll() {
  fetchPanel('/api/dashboard', 'p-dashboard', (d) => {
    const sigMode = document.getElementById('sig-mode');
    if (d.mock_mode) {
      sigMode.textContent = 'MOCK MODE';
      sigMode.className = 'signal-pill mock';
    } else if (d.live) {
      sigMode.textContent = 'LIVE';
      sigMode.className = 'signal-pill live';
    } else {
      sigMode.textContent = 'UNKNOWN MODE';
    }
  });
  fetchPanel('/api/bandit', 'p-bandit');
  fetchPanel('/api/cli-pool', 'p-clipool');
  fetchPanel('/api/learnings/summary', 'p-learnings');
  fetchPanel('/api/spend', 'p-spend', (d) => {
    const sigCost = document.getElementById('sig-cost');
    let source = "unknown";
    if (d && typeof d === 'object') {
        if (d.estimate_source_breakdown) {
            const keys = Object.keys(d.estimate_source_breakdown);
            if(keys.length > 0) source = keys.join(', ');
        }
        if (d.estimate_source) {
            source = d.estimate_source;
        }
    }
    sigCost.textContent = 'Cost source: ' + source;
  });
  fetchPanel('/api/goals', 'p-goals');
  fetchPanel('/api/cliproxy/status', 'p-cliproxy');
}
loadAll();
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
