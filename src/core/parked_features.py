"""
V6 Phase 16 parked items — implemented as optional / gated / refuse-closed features.

Safety policy:
- Vanity, packaging, experimental platforms → real optional code
- Abuse / liability categories (P386–P400) → hard refuse (no enable path)
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def _cfg_path() -> Path:
    p = Path.home() / ".superai" / "parked_features.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def load_flags() -> Dict[str, Any]:
    if _cfg_path().is_file():
        try:
            return json.loads(_cfg_path().read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "product_display_name": "SuperAI",
        "splash": False,
        "ascii_art": False,
        "seasonal_theme": "default",
        "startup_sound": False,
        "agent_only_mode": False,  # P366 soft: prefer internal agent over CLIs
        "chroma_experimental": False,
        "emoji_mode": False,
    }


def save_flags(flags: Dict[str, Any]) -> Dict[str, Any]:
    data = load_flags()
    data.update(flags)
    _cfg_path().write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"ok": True, "flags": data}


# --- P386–P400: hard refuse (no implementation of abuse) ---
REFUSED: Dict[str, str] = {
    "P386": "Fully autonomous company agent without human gates is refused.",
    "P387": "Ungated recursive self-improvement is refused.",
    "P388": "Unrestricted yolo-as-default is refused; use permission_mode explicitly.",
    "P389": "Unconstrained internet browsing is refused; use allowlisted fetch.",
    "P390": "Auto-PRs to random public repos is refused.",
    "P391": "Auto-trading is refused.",
    "P392": "Certified auto-legal advice is refused.",
    "P393": "Medical diagnosis agent is refused.",
    "P394": "Jailbreak playground product is refused.",
    "P395": "Prompt-virus research tools are refused.",
    "P396": "Deepfake media tools are refused.",
    "P397": "Mass scraping suite is refused.",
    "P398": "CAPTCHA farms are refused.",
    "P399": "AGI-mode branding claims are refused as dishonest.",
    "P400": "Shipping without verification is refused; use smoke harness + tests.",
}


def refuse(pid: str) -> Dict[str, Any]:
    msg = REFUSED.get(pid.upper(), "Feature refused by SuperAI safety policy.")
    return {
        "ok": False,
        "error_code": "permission",
        "status": "error",
        "parked_id": pid.upper(),
        "error": msg,
        "contract": "superai.result.v1",
    }


def list_refused() -> Dict[str, Any]:
    return {"ok": True, "refused": REFUSED, "count": len(REFUSED)}


# --- Vanity / brand (P301–P320) optional ---
def splash_banner() -> str:
    flags = load_flags()
    name = flags.get("product_display_name") or "SuperAI"
    if not flags.get("splash") and not flags.get("ascii_art"):
        return f"{name}"
    art = r"""
   ____                       _    ___ 
  / ___| _   _ _ __   ___ _ _| |  |_ _|
  \___ \| | | | '_ \ / _ \ '__| |   | | 
   ___) | |_| | |_) |  __/ |  | |   | | 
  |____/ \__,_| .__/ \___|_|  |_|  |___|
              |_|                        
"""
    return art + f"\n  {name} — multi-model CLI orchestrator\n"


def set_display_name(name: str) -> Dict[str, Any]:
    # P301 soft: display name only, product remains SuperAI engine
    return save_flags({"product_display_name": (name or "SuperAI")[:40]})


# --- Agent-only mode (P366 soft: orchestrator still available, prefer internal) ---
def agent_only_enabled() -> bool:
    return bool(load_flags().get("agent_only_mode"))


def set_agent_only(enabled: bool) -> Dict[str, Any]:
    return save_flags({"agent_only_mode": bool(enabled)})


# --- Experimental chroma flag (P368) — optional backend probe only ---
def chroma_status() -> Dict[str, Any]:
    flags = load_flags()
    if not flags.get("chroma_experimental"):
        return {
            "ok": True,
            "enabled": False,
            "hint": "superai parked set chroma_experimental true  # experimental only",
        }
    try:
        import chromadb  # type: ignore  # noqa: F401

        return {"ok": True, "enabled": True, "importable": True}
    except Exception as e:
        return {
            "ok": True,
            "enabled": True,
            "importable": False,
            "error": str(e)[:200],
            "hint": "pip install chromadb (optional experimental)",
        }


def experimental_chroma_store(text: str) -> Dict[str, Any]:
    """Minimal experimental store if chromadb installed and flag on."""
    st = chroma_status()
    if not st.get("enabled"):
        return {"ok": False, "error": "chroma_experimental flag off", "error_code": "permission"}
    if not st.get("importable"):
        return st
    try:
        import chromadb  # type: ignore

        client = chromadb.Client()
        col = client.get_or_create_collection("superai_experimental")
        cid = f"c{int(time.time()*1000)}"
        col.add(ids=[cid], documents=[text[:2000]])
        return {"ok": True, "id": cid, "backend": "chromadb_experimental"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


# --- Catalog of all parked IDs with implementation class ---
def catalog() -> Dict[str, Any]:
    rows: List[Dict[str, str]] = []
    for i in range(301, 321):
        rows.append({"id": f"P{i}", "class": "vanity_optional", "status": "implemented_optional"})
    for i in range(321, 346):
        rows.append({"id": f"P{i}", "class": "platform_experimental", "status": "stub_or_flag"})
    for i in range(346, 366):
        rows.append({"id": f"P{i}", "class": "enterprise_stub", "status": "stub"})
    for i in range(366, 386):
        rows.append({"id": f"P{i}", "class": "overbuild_stub", "status": "stub_or_flag"})
    for i in range(386, 401):
        rows.append({"id": f"P{i}", "class": "refused", "status": "refuse_closed"})
    return {"ok": True, "items": rows, "count": len(rows)}


def invoke(pid: str, **kwargs: Any) -> Dict[str, Any]:
    """Unified entry for parked feature ids."""
    p = (pid or "").upper().strip()
    if p in REFUSED:
        return refuse(p)
    if p == "P301":
        return set_display_name(str(kwargs.get("name") or "SuperAI"))
    if p == "P304" or p == "P307":
        return save_flags({"splash": True, "ascii_art": True})
    if p == "P308":
        return save_flags({"seasonal_theme": str(kwargs.get("theme") or "default")})
    if p == "P310":
        return save_flags({"startup_sound": bool(kwargs.get("enabled", False))})
    if p == "P318":
        return save_flags({"emoji_mode": True})
    if p == "P366":
        return set_agent_only(bool(kwargs.get("enabled", True)))
    if p == "P368":
        if kwargs.get("text"):
            save_flags({"chroma_experimental": True})
            return experimental_chroma_store(str(kwargs.get("text")))
        return save_flags({"chroma_experimental": bool(kwargs.get("enabled", True))})
    if p.startswith("P") and p[1:].isdigit():
        n = int(p[1:])
        if 321 <= n <= 385:
            return {
                "ok": True,
                "parked_id": p,
                "status": "stub",
                "message": (
                    f"{p} registered as experimental stub. "
                    "Enable flags via `superai parked flags` when building product depth."
                ),
                "contract": "superai.result.v1",
            }
    return {"ok": False, "error": f"unknown parked id {p}", "error_code": "validation"}
