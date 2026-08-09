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

    console_dir = Path(__file__).resolve().parent / "static" / "console"
    if console_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(console_dir)), name="static")


    # AI Council Integration
    try:
        import sys
        council_dir = Path(__file__).resolve().parents[2] / "projects" / "ai-council"
        council_backend = council_dir / "backend"
        council_frontend = council_dir / "frontend" / "dist"
        
        if council_backend.is_dir() and council_frontend.is_dir():
            if str(council_backend) not in sys.path:
                sys.path.append(str(council_backend))
            
            from main import app as council_api
            app.mount("/council-api", council_api)
            app.mount("/council", StaticFiles(directory=str(council_frontend), html=True), name="council_frontend")
    except Exception:
        pass


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

    def _check_management_auth(req: Request) -> None:
        """
        Management token required unconditionally (including loopback).
        Header-bearer auth is CSRF-safe by construction: a foreign page cannot attach
        the Authorization header without already holding the token. This holds only
        while the token is never stored in a cookie.
        """
        if not management_token:
            raise HTTPException(status_code=401, detail="Management token not configured")
            
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

    if enable_config_write:
        if not management_token:
            import logging
            logging.getLogger("superai.web_app").error("SUPERAI_WEB_ENABLE_CONFIG_WRITE is on but SUPERAI_WEB_MANAGEMENT_TOKEN is unset. Write routes will NOT be enabled.")
        else:

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

            @app.api_route("/api/config/diff", methods=["GET", "POST"])
            async def config_diff(request: Request) -> Dict[str, Any]:
                _check_management_auth(request)
                try:
                    payload = await request.json()
                except Exception:
                    payload = {}
                changes = payload.get("changes", {})
                from core.config import diff_changes
                diff_text = diff_changes(changes)
                return {"ok": True, "diff": diff_text}

            @app.get("/api/config/backups")
            async def get_config_backups(request: Request) -> Dict[str, Any]:
                _check_management_auth(request)
                from core.config import Config
                cfg = Config()
                backups_dir = cfg.home_dir / "backups"
                backups_list = []
                if backups_dir.exists():
                    for f in sorted(backups_dir.glob("config-*.json"), reverse=True):
                        st = f.stat()
                        backups_list.append({
                            "id": f.name,
                            "timestamp": st.st_mtime,
                            "size": st.st_size
                        })
                return {"ok": True, "backups": backups_list}

            @app.post("/api/config/rollback")
            async def rollback_config(request: Request) -> Dict[str, Any]:
                _check_management_auth(request)
                payload = await request.json()
                backup_id = payload.get("backup_id")
                if not backup_id or not isinstance(backup_id, str):
                    raise HTTPException(status_code=400, detail="backup_id required")
                if ".." in backup_id or "/" in backup_id or "\\" in backup_id:
                    raise HTTPException(status_code=400, detail="invalid backup_id")
                
                from core.config import Config
                from core.audit_log import AuditLog
                import shutil
                cfg = Config()
                backups_dir = cfg.home_dir / "backups"
                backup_path = backups_dir / backup_id
                
                if not backup_path.is_file() or backup_path.parent != backups_dir:
                    raise HTTPException(status_code=400, detail="backup not found")
                
                # Backup current before rollback
                cfg.save() 
                
                # Rollback atomically
                tmp_path = cfg.config_path.with_suffix(".json.tmp")
                shutil.copy2(backup_path, tmp_path)
                import os
                with open(tmp_path, "r+b") as _f:
                    _f.flush()
                    os.fsync(_f.fileno())
                os.replace(tmp_path, cfg.config_path)
                
                AuditLog().record("config.rollback", detail={"source_backup_id": backup_id}, actor="web", outcome="success")
                
                return {"ok": True, "status": "rolled_back", "backup_id": backup_id}

            @app.get("/api/models")
            async def get_models(request: Request) -> Dict[str, Any]:
                _check_management_auth(request)
                from core.model_registry import ModelRegistry
                registry = ModelRegistry()
                
                models_list = []
                for m in registry.models.values():
                    row = {
                        "name": m.name,
                        "provider": m.provider,
                        "model_id": m.model_id,
                        "base_url": m.base_url,
                        "api_key_env": m.api_key_env,
                        "context_window": m.context_window,
                        "is_latest": m.is_latest,
                        "supports_tools": m.supports_tools,
                        "strengths": m.strengths,
                        "cost_per_1k_tokens": m.cost_per_1k_tokens,
                        "latency_tier": m.latency_tier,
                        "source_file": m.source_file,
                        **m.extra,
                    }
                    models_list.append(row)
                
                return {"ok": True, "models": models_list, "source": registry.source}

            @app.post("/api/models")
            async def update_models(request: Request) -> Dict[str, Any]:
                _check_management_auth(request)
                payload = await request.json()
                models_data = payload.get("models")
                if not isinstance(models_data, list):
                    raise HTTPException(status_code=400, detail="models must be a list")
                
                from core.model_registry import ModelInfo
                import dataclasses
                import json
                allowed_fields = {f.name for f in dataclasses.fields(ModelInfo) if f.name not in ('extra', 'source_file')}
                
                valid_models = []
                errors = []
                for idx, row in enumerate(models_data):
                    if not isinstance(row, dict):
                        errors.append(f"Row {idx}: must be an object")
                        continue
                    if "name" not in row or not isinstance(row["name"], str):
                        errors.append(f"Row {idx}: missing or invalid 'name'")
                        continue
                    
                    unknown = [k for k in row.keys() if k not in allowed_fields]
                    if unknown:
                        errors.append(f"Row {idx}: unknown fields {unknown}")
                        continue
                    
                    try:
                        # minimal type check on numeric fields if present
                        if "context_window" in row:
                            int(row["context_window"])
                        if "cost_per_1k_tokens" in row:
                            float(row["cost_per_1k_tokens"])
                        if "latency_tier" in row:
                            int(row["latency_tier"])
                    except (ValueError, TypeError):
                        errors.append(f"Row {idx}: type conversion error for numeric fields")
                        continue
                        
                    valid_models.append(row)
                
                if errors:
                    from core.audit_log import AuditLog
                    AuditLog().record("models.write", detail={"errors": errors}, actor="web", outcome="failure")
                    raise HTTPException(status_code=400, detail={"errors": errors})
                
                from pathlib import Path
                target_path = Path.home() / ".superai" / "config" / "models.json"
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                from core.config import atomic_write_with_backup
                backups_dir = Path.home() / ".superai" / "backups"
                
                atomic_write_with_backup(target_path, valid_models, backups_dir)
                
                from core.audit_log import AuditLog
                AuditLog().record("models.write", detail={"count": len(valid_models)}, actor="web", outcome="success")
                
                return {"ok": True, "status": "updated", "count": len(valid_models)}

            @app.get("/api/{resource}")
            async def get_resource(request: Request, resource: str) -> Dict[str, Any]:
                if resource not in ("quotas", "key_pools", "aliases", "rate_limits", "payload_rules"):
                    raise HTTPException(status_code=404)
                _check_management_auth(request)
                import json
                from pathlib import Path
                path = Path.home() / ".superai" / "config" / f"{resource}.json"
                if path.exists():
                    try:
                        return {"ok": True, "data": json.loads(path.read_text(encoding="utf-8"))}
                    except Exception as e:
                        return {"ok": False, "error": str(e)}
                return {"ok": True, "data": {}}

            @app.post("/api/{resource}")
            async def set_resource(request: Request, resource: str) -> Dict[str, Any]:
                if resource not in ("quotas", "key_pools", "aliases", "rate_limits", "payload_rules"):
                    raise HTTPException(status_code=404)
                _check_management_auth(request)
                import json
                from pathlib import Path
                try:
                    payload = await request.json()
                except json.JSONDecodeError:
                    raise HTTPException(status_code=400, detail="Invalid JSON in request body")
                
                data = payload.get("data", payload)
                
                if resource == "quotas":
                    from core.quota_manager import QuotaManager
                    qm = QuotaManager()
                    qm.data = data
                    qm._save()
                elif resource == "key_pools":
                    from core.key_pool import KeyPool
                    kp = KeyPool()
                    kp.pools = data.get("pools", {})
                    kp.indexes = data.get("indexes", {})
                    kp._save()
                elif resource == "aliases":
                    from core.model_router import AliasRouter
                    ar = AliasRouter()
                    ar.aliases = data.get("aliases", {})
                    ar._save()
                elif resource == "rate_limits":
                    from core.rate_limiter import TokenBucketRateLimiter
                    tb = TokenBucketRateLimiter()
                    tb.limits = data.get("limits", {})
                    tb._save()
                elif resource == "payload_rules":
                    from core.payload_rules import PersistentPayloadRules
                    pr = PersistentPayloadRules()
                    pr.blocked_keywords = data.get("blocked_keywords", [])
                    pr.system_prompt_appends = data.get("system_prompt_appends", [])
                    pr._save()
                else:
                    path = Path.home() / ".superai" / "config" / f"{resource}.json"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                    
                return {"ok": True}
    @app.get("/api/audit")
    async def api_audit(request: Request, limit: int = Query(50, ge=1, le=500)) -> Dict[str, Any]:
        _check_management_auth(request)
        from core.audit_log import AuditLog
        return {"ok": True, "entries": AuditLog().recent(limit=limit)}

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
 <a href="/dashboard">Dashboard</a> &middot; <a href="/cli-pool">CLI Pool</a> &middot;
 <a href="/terminals">Terminals</a> &middot; <a href="/palace">Palace</a> &middot;
 <a href="/mcp">MCP</a> &middot;
 <a href="/council">AI Council</a> &middot;
 <a href="/charts">Charts</a> &middot; <a href="/pwa/">PWA</a></p>
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

    # Helper to proxy requests to CLIProxyAPI gateway
    def _proxy_cliproxy_request(target_path: str, req: Request, method: str, body_bytes: bytes = b"") -> Any:
        import urllib.request
        import urllib.error
        from core.provider_catalog import OPENAI_COMPAT_PROVIDERS

        cfg = OPENAI_COMPAT_PROVIDERS.get("cliproxy", {})
        base_url = cfg.get("base_url", "http://127.0.0.1:8317/v1")
        if base_url.endswith("/v1"):
            root_url = base_url[:-3]
        else:
            root_url = base_url.rstrip("/")

        target_url = f"{root_url}/{target_path.lstrip('/')}"
        query_str = str(req.url.query) if req.url.query else ""
        if query_str:
            target_url = f"{target_url}?{query_str}"

        forward_headers = {}
        for k, v in req.headers.items():
            if k.lower() in {"authorization", "content-type", "accept", "x-management-key", "x-superai-management-token"}:
                forward_headers[k] = v

        url_req = urllib.request.Request(
            target_url,
            data=body_bytes if method in {"POST", "PUT", "PATCH"} and body_bytes else None,
            headers=forward_headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(url_req, timeout=10.0) as resp:
                resp_body = resp.read()
                resp_headers = dict(resp.headers)
                return Response(
                    content=resp_body,
                    status_code=resp.status,
                    headers={k: v for k, v in resp_headers.items() if k.lower() not in {"content-length", "transfer-encoding"}},
                    media_type=resp_headers.get("content-type", "application/json"),
                )
        except urllib.error.HTTPError as e:
            err_body = e.read()
            return Response(
                content=err_body,
                status_code=e.code,
                headers=dict(e.headers),
                media_type="application/json",
            )
        except Exception as e:
            return JSONResponse(
                status_code=502,
                content={
                    "ok": False,
                    "error": f"CLIProxyAPI daemon is offline or unreachable at {root_url}",
                    "reachable": False,
                    "detail": str(e),
                },
            )



    @app.api_route("/v1/models", methods=["GET"])
    async def proxy_models_endpoint(request: Request):
        return _proxy_cliproxy_request("v1/models", request, "GET")

    @app.post("/api/sync/cliproxy")
    async def api_sync_cliproxy(request: Request) -> Dict[str, Any]:
        """
        Bidirectional auto-sync: query CLIProxyAPI's active models and sync them
        into SuperAI's ~/.superai/config/models.json & ModelRegistry.
        """
        from core.model_registry import ModelRegistry
        from core.provider_catalog import OPENAI_COMPAT_PROVIDERS
        from core.audit_log import AuditLog
        import json
        import urllib.request

        cfg = OPENAI_COMPAT_PROVIDERS.get("cliproxy", {})
        base_url = cfg.get("base_url", "http://127.0.0.1:8317/v1")
        models_url = f"{base_url.rstrip('/')}/models"

        discovered_models = []
        is_live_sync = False
        try:
            req = urllib.request.Request(models_url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, dict) and "data" in data:
                    discovered_models = data["data"]
                elif isinstance(data, list):
                    discovered_models = data
                is_live_sync = True
        except Exception:
            # Fallback to vendored reference models if daemon is not currently active
            vendor_models_file = Path(__file__).resolve().parents[2] / "vendor" / "cliproxy-models" / "models.json"
            if vendor_models_file.is_file():
                try:
                    vdata = json.loads(vendor_models_file.read_text(encoding="utf-8"))
                    for key, mlist in vdata.items():
                        if isinstance(mlist, list):
                            for m in mlist:
                                if isinstance(m, dict) and "id" in m:
                                    discovered_models.append(m)
                                elif isinstance(m, str):
                                    discovered_models.append({"id": m})
                except Exception:
                    pass

        registry = ModelRegistry()
        result = registry.sync_cliproxy_models(discovered_models)
        result["live_sync"] = is_live_sync
        result["source_url"] = models_url if is_live_sync else "vendored_fallback"

        AuditLog().record(
            "cliproxy.sync",
            detail={"count": len(discovered_models), "live": is_live_sync},
            actor="web",
            outcome="success",
        )

        return result

    @app.get("/api/sync/status")
    def api_sync_status() -> Dict[str, Any]:
        """Check status of bidirectional sync bridge."""
        from core.model_registry import ModelRegistry
        from core.provider_catalog import OPENAI_COMPAT_PROVIDERS
        from core.smoke_preflight import check_local_up

        cfg = OPENAI_COMPAT_PROVIDERS.get("cliproxy", {})
        base_url = cfg.get("base_url", "http://127.0.0.1:8317/v1")
        reachable = check_local_up("cliproxy", timeout=1.5)

        registry = ModelRegistry()
        cliproxy_models = [m.name for m in registry.models.values() if m.provider == "cliproxy" or m.name.startswith("cliproxy:")]

        return {
            "ok": True,
            "bridge_active": True,
            "proxy_reachable": reachable,
            "configured_base_url": base_url,
            "synced_models_count": len(cliproxy_models),
            "synced_models": cliproxy_models,
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
<p><a href="/">Memory</a> · <a href="/charts">Charts</a> · <a href="/council">AI Council</a> · <button onclick="load()">Refresh</button></p>
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
    @app.get("/management.html", response_class=HTMLResponse)
    def console_page() -> Any:
        from fastapi.responses import FileResponse
        console_path = Path(__file__).resolve().parent / "static" / "console" / "index.html"
        if console_path.is_file():
            return FileResponse(str(console_path))
        return HTMLResponse("<h1>Console UI not built. Please create static/console/index.html</h1>", status_code=404)

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
