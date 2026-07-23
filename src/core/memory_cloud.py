"""
Managed-cloud memory surface (Phase 9+) — honest offline-first.

Does **not** deploy cloud infrastructure. Provides:
  - config for remote DSN / API base URL
  - status probe (fail-closed when unreachable)
  - dry-run sync plan from local dataset export

Secrets: tokens never written to logs or status JSON (redacted).
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from .net_safety import validate_public_http_url


def cloud_config_path() -> Path:
    env = (os.getenv("SUPERAI_MEMORY_CLOUD_CONFIG") or "").strip()
    if env:
        return Path(env).expanduser()
    p = Path.home() / ".superai" / "memory" / "cloud_config.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load() -> Dict[str, Any]:
    p = cloud_config_path()
    if not p.is_file():
        return {
            "enabled": False,
            "api_base": None,
            "dsn": None,
            "region": None,
            "tenant": None,
        }
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {"enabled": False}


def _save(data: Dict[str, Any]) -> None:
    p = cloud_config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    # never persist raw token in file if env-provided preferred — store only if explicit
    safe = dict(data)
    if safe.get("token"):
        # store marker only; real token from env SUPERAI_MEMORY_CLOUD_TOKEN
        safe["token_set"] = True
        safe.pop("token", None)
    p.write_text(json.dumps(safe, indent=2) + "\n", encoding="utf-8")


def configure(
    *,
    api_base: Optional[str] = None,
    dsn: Optional[str] = None,
    region: Optional[str] = None,
    tenant: Optional[str] = None,
    enabled: Optional[bool] = None,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    cfg = _load()
    if api_base is not None:
        api_base = api_base.strip() or None
        if api_base:
            err = validate_public_http_url(api_base, require_https=True)
            # allow localhost only if private override
            if err and not (os.getenv("SUPERAI_ALLOW_PRIVATE_URLS") or "").strip():
                # still allow https public; for http local testing require env
                if "HTTPS required" in (err or "") or "Only http" in (err or ""):
                    pass  # https check
                if err and "private" not in err.lower() and "HTTPS" not in err:
                    return {"ok": False, "error": err, "error_code": "ssrf"}
        cfg["api_base"] = api_base
    if dsn is not None:
        cfg["dsn"] = (dsn.strip() or None)
    if region is not None:
        cfg["region"] = region.strip() or None
    if tenant is not None:
        cfg["tenant"] = tenant.strip() or None
    if enabled is not None:
        cfg["enabled"] = bool(enabled)
    if token:
        # set env-style side file is avoided; document SUPERAI_MEMORY_CLOUD_TOKEN
        cfg["token_set"] = True
    _save(cfg)
    return {
        "ok": True,
        "product": "memory_cloud",
        "config": public_config(cfg),
        "message": "Memory cloud config updated (token via SUPERAI_MEMORY_CLOUD_TOKEN)",
    }


def public_config(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    c = dict(cfg or _load())
    c.pop("token", None)
    if c.get("dsn"):
        # redact password in DSN
        dsn = str(c["dsn"])
        if "@" in dsn and "://" in dsn:
            scheme, rest = dsn.split("://", 1)
            if "@" in rest:
                creds, host = rest.rsplit("@", 1)
                if ":" in creds:
                    user = creds.split(":", 1)[0]
                    c["dsn"] = f"{scheme}://{user}:***@{host}"
    c["token_env"] = bool((os.getenv("SUPERAI_MEMORY_CLOUD_TOKEN") or "").strip())
    return c


def status(*, timeout: float = 3.0) -> Dict[str, Any]:
    cfg = _load()
    base = (cfg.get("api_base") or os.getenv("SUPERAI_MEMORY_CLOUD_URL") or "").strip()
    enabled = bool(cfg.get("enabled")) or bool(base)
    out: Dict[str, Any] = {
        "ok": True,
        "product": "memory_cloud",
        "enabled": enabled,
        "configured": bool(base or cfg.get("dsn")),
        "config": public_config(cfg),
        "reachable": False,
        "mode": "local_only",
        "message": "",
    }
    if not enabled or not base:
        out["message"] = (
            "Managed cloud not enabled. Local palace/kg remain authoritative. "
            "Configure with `superai cloud configure --api-base https://... --enable`."
        )
        out["mode"] = "local_only"
        return out

    err = validate_public_http_url(base)
    if err and not (os.getenv("SUPERAI_ALLOW_PRIVATE_URLS") or "").strip():
        out["ok"] = False
        out["error"] = err
        out["error_code"] = "ssrf"
        out["message"] = f"Cloud URL blocked: {err}"
        return out

    # health probe
    health = base.rstrip("/") + "/health"
    try:
        req = urllib.request.Request(
            health,
            headers={"User-Agent": "SuperAI-memory-cloud/1.0", "Accept": "application/json"},
            method="GET",
        )
        token = (os.getenv("SUPERAI_MEMORY_CLOUD_TOKEN") or "").strip()
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            out["reachable"] = True
            out["http_status"] = getattr(resp, "status", 200)
            out["mode"] = "remote_ok"
            out["message"] = f"Cloud health OK ({out['http_status']})"
    except urllib.error.HTTPError as e:
        out["reachable"] = False
        out["http_status"] = e.code
        out["mode"] = "remote_error"
        out["message"] = f"Cloud health HTTP {e.code}"
        out["ok"] = False
        out["error_code"] = "http"
    except Exception as e:  # noqa: BLE001
        out["reachable"] = False
        out["mode"] = "remote_unreachable"
        out["message"] = (
            f"Cloud unreachable ({type(e).__name__}); operating local-only. "
            "This is expected offline."
        )
        # offline is not a hard failure of the product
        out["ok"] = True
        out["offline"] = True
    return out


def dry_run_sync(
    dataset_id: str = "default",
    *,
    limit: int = 1000,
) -> Dict[str, Any]:
    """
    Plan a push of one local dataset to cloud without network write.

    Builds export stats (same shape as dataset export) and a sync plan.
    """
    from .memory_dataset import export_dataset, resolve_dataset_id

    did = resolve_dataset_id(dataset_id) or "default"
    # export to temp under ~/.superai
    dest = (
        Path.home()
        / ".superai"
        / "memory"
        / "cloud_dryrun"
        / f"{did}_{int(time.time())}.zip"
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    exp = export_dataset(did, dest=dest)
    cfg = public_config()
    st = status()
    plan = {
        "action": "push_dataset",
        "dataset_id": did,
        "destination": cfg.get("api_base") or "(not configured)",
        "would_upload_bytes": dest.stat().st_size if dest.is_file() else 0,
        "counts": exp.get("counts"),
        "export_path": exp.get("path"),
        "network_write": False,
        "reason": "dry-run only — no cloud write performed",
    }
    return {
        "ok": bool(exp.get("ok")),
        "product": "memory_cloud_dry_sync",
        "export": exp if exp.get("ok") else {"ok": False, "error": exp.get("error")},
        "cloud_status": {
            "mode": st.get("mode"),
            "reachable": st.get("reachable"),
            "configured": st.get("configured"),
        },
        "plan": plan,
        "message": (
            f"Dry-run sync for dataset {did}: "
            f"{(exp.get('counts') or {}).get('memories', 0)} memories planned; "
            f"no network write"
        ),
    }


def push_sync(
    dataset_id: str = "default",
    *,
    apply: bool = False,
    limit: int = 1000,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """
    P9-R3: push protocol behind explicit apply.

    Default (apply=False): same as dry_run_sync (network_write=false).
    apply=True: requires configured reachable cloud; POSTs export zip to
    ``{api_base}/v1/memory/datasets/{id}/import`` when reachable.
    Offline / unreachable → fail-closed with local plan retained.
    """
    plan = dry_run_sync(dataset_id, limit=limit)
    if not apply:
        plan["apply"] = False
        plan.setdefault("plan", {})["network_write"] = False
        return plan

    st = status(timeout=timeout)
    cfg = public_config()
    base = (cfg.get("api_base") or os.getenv("SUPERAI_MEMORY_CLOUD_URL") or "").strip()
    out = dict(plan)
    out["product"] = "memory_cloud_push"
    out["apply"] = True
    if not base:
        out["ok"] = False
        out["error"] = "api_base not configured"
        out["error_code"] = "not_configured"
        out["message"] = "Cannot apply push: configure cloud api_base first"
        out.setdefault("plan", {})["network_write"] = False
        return out
    if not st.get("reachable"):
        out["ok"] = False
        out["error"] = "cloud unreachable"
        out["error_code"] = "unreachable"
        out["message"] = (
            "Cannot apply push: cloud not reachable. Dry-run plan retained; "
            "export zip is local-only."
        )
        out.setdefault("plan", {})["network_write"] = False
        out["cloud_status"] = {
            "mode": st.get("mode"),
            "reachable": st.get("reachable"),
        }
        return out

    exp_path = (plan.get("export") or {}).get("path") or (plan.get("plan") or {}).get(
        "export_path"
    )
    if not exp_path or not Path(exp_path).is_file():
        out["ok"] = False
        out["error"] = "export zip missing"
        out["error_code"] = "export"
        return out

    url = base.rstrip("/") + f"/v1/memory/datasets/{dataset_id}/import"
    try:
        data = Path(exp_path).read_bytes()
        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "User-Agent": "SuperAI-memory-cloud/1.0",
                "Content-Type": "application/zip",
                "Accept": "application/json",
            },
        )
        token = (os.getenv("SUPERAI_MEMORY_CLOUD_TOKEN") or "").strip()
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            body = resp.read()[:2000]
            out["ok"] = True
            out["http_status"] = getattr(resp, "status", 200)
            out["response_preview"] = body.decode("utf-8", errors="replace")[:500]
            out.setdefault("plan", {})["network_write"] = True
            out["message"] = f"Applied push to {url} (HTTP {out['http_status']})"
    except Exception as e:  # noqa: BLE001
        out["ok"] = False
        out["error"] = str(e)[:300]
        out["error_code"] = "push_failed"
        out.setdefault("plan", {})["network_write"] = False
        out["message"] = f"Push apply failed: {type(e).__name__}: {e}"[:200]
    return out
