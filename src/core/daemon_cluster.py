"""
Multi-host SuperAI goals/schedules cluster coordination (N206 expansion).

Local-first design (no required Redis/etcd):
- Shared membership + leader lease file (NFS/SMB/local path via SUPERAI_CLUSTER_STORE)
- Heartbeat registration for each host
- Leader election by latest valid lease (TTL)
- Job sharding: schedule job ids hashed to host index when not leader-only mode

Modes:
- leader_only: only leader runs ticks (default for execute_goals safety)
- sharded: all healthy hosts run, each takes jobs where hash(job_id) % n == host_index
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


def default_host_id() -> str:
    env = (os.getenv("SUPERAI_CLUSTER_HOST_ID") or "").strip()
    if env:
        return env
    try:
        return f"{socket.gethostname()}-{os.getpid()}"
    except Exception:
        return f"host-{uuid.uuid4().hex[:8]}"


def cluster_store_path() -> Path:
    raw = (os.getenv("SUPERAI_CLUSTER_STORE") or "").strip()
    if raw:
        p = Path(raw)
    else:
        p = Path.home() / ".superai" / "cluster" / "membership.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _now() -> float:
    return time.time()


def _load() -> Dict[str, Any]:
    path = cluster_store_path()
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {"hosts": {}, "leader": None, "lease_until": 0, "updated_at": None}


def _save(data: Dict[str, Any]) -> None:
    path = cluster_store_path()
    data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    payload = json.dumps(data, indent=2)
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(payload, encoding="utf-8")
    # Windows can deny replace if AV/indexer holds the target briefly
    last_err: Optional[Exception] = None
    for _ in range(8):
        try:
            os.replace(str(tmp), str(path))
            return
        except PermissionError as e:
            last_err = e
            time.sleep(0.02)
        except OSError as e:
            last_err = e
            time.sleep(0.02)
    try:
        path.write_text(payload, encoding="utf-8")
    except Exception:
        if last_err:
            raise last_err
        raise
    finally:
        try:
            if tmp.is_file():
                tmp.unlink()
        except Exception:
            pass


def heartbeat(
    *,
    host_id: Optional[str] = None,
    ttl_sec: float = 90.0,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Register/refresh this host and attempt leader election."""
    from .spend_guard import ensure_public_result

    hid = host_id or default_host_id()
    ttl = max(15.0, float(ttl_sec))
    now = _now()
    data = _load()
    hosts = data.setdefault("hosts", {})
    hosts[hid] = {
        "host_id": hid,
        "last_seen": now,
        "expires": now + ttl,
        "meta": meta or {},
    }
    # prune dead
    hosts = {
        k: v
        for k, v in hosts.items()
        if float(v.get("expires") or 0) > now
    }
    data["hosts"] = hosts

    leader = data.get("leader")
    lease_until = float(data.get("lease_until") or 0)
    # renew if we are leader
    if leader == hid and lease_until > now:
        data["lease_until"] = now + ttl
        is_leader = True
    elif not leader or lease_until <= now or leader not in hosts:
        # elect: stable sort host ids, pick first healthy
        ordered = sorted(hosts.keys())
        if ordered:
            data["leader"] = ordered[0]
            data["lease_until"] = now + ttl
        is_leader = data.get("leader") == hid
    else:
        is_leader = leader == hid

    # if we lost leadership but lease expired on them, already handled
    _save(data)
    healthy = sorted(hosts.keys())
    return ensure_public_result(
        {
            "ok": True,
            "host_id": hid,
            "is_leader": is_leader,
            "leader": data.get("leader"),
            "lease_until": data.get("lease_until"),
            "healthy_hosts": healthy,
            "host_count": len(healthy),
            "host_index": healthy.index(hid) if hid in healthy else -1,
            "store": str(cluster_store_path()),
            "ttl_sec": ttl,
        },
        ok=True,
    )


def cluster_status() -> Dict[str, Any]:
    from .spend_guard import ensure_public_result

    data = _load()
    now = _now()
    hosts = {
        k: v
        for k, v in (data.get("hosts") or {}).items()
        if float(v.get("expires") or 0) > now
    }
    leader = data.get("leader")
    lease_until = float(data.get("lease_until") or 0)
    if leader and (leader not in hosts or lease_until <= now):
        leader = None
    return ensure_public_result(
        {
            "ok": True,
            "leader": leader,
            "lease_until": lease_until if leader else None,
            "hosts": hosts,
            "host_count": len(hosts),
            "store": str(cluster_store_path()),
            "mode_env": os.getenv("SUPERAI_CLUSTER_MODE") or "single",
        },
        ok=True,
    )


def should_run_tick(
    *,
    host_id: Optional[str] = None,
    mode: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Decide if this host should run a daemon tick / execute goals.
    """
    mode = (mode or os.getenv("SUPERAI_CLUSTER_MODE") or "leader_only").lower()
    hb = heartbeat(host_id=host_id)
    hid = hb.get("host_id")
    is_leader = bool(hb.get("is_leader"))
    if mode in {"off", "disabled", "single"}:
        return {
            "ok": True,
            "run_tick": True,
            "run_execute": True,
            "mode": "single",
            "is_leader": True,
            "host_id": hid,
            "reason": "cluster_disabled",
        }
    if mode == "leader_only":
        return {
            "ok": True,
            "run_tick": is_leader,
            "run_execute": is_leader,
            "mode": mode,
            "is_leader": is_leader,
            "host_id": hid,
            "leader": hb.get("leader"),
            "reason": "leader_only" if is_leader else "follower_skip",
        }
    # sharded: all run ticks; execute only on leader (safer) unless SUPERAI_CLUSTER_SHARD_EXECUTE=1
    shard_exec = (os.getenv("SUPERAI_CLUSTER_SHARD_EXECUTE") or "").lower() in {
        "1",
        "true",
        "yes",
    }
    return {
        "ok": True,
        "run_tick": True,
        "run_execute": is_leader or shard_exec,
        "mode": "sharded",
        "is_leader": is_leader,
        "host_id": hid,
        "host_index": hb.get("host_index"),
        "host_count": hb.get("host_count"),
        "reason": "sharded",
    }


def shard_owns(job_id: str, host_index: int, host_count: int) -> bool:
    if host_count <= 1 or host_index < 0:
        return True
    h = int(hashlib.sha256(str(job_id).encode()).hexdigest()[:8], 16)
    return (h % host_count) == (host_index % host_count)


def filter_jobs_for_host(
    jobs: List[Dict[str, Any]],
    *,
    host_index: int,
    host_count: int,
) -> List[Dict[str, Any]]:
    if host_count <= 1:
        return list(jobs)
    return [
        j
        for j in jobs
        if shard_owns(str(j.get("id") or j.get("name") or ""), host_index, host_count)
    ]
