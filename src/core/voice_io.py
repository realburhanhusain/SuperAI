"""
Voice I/O for SuperAI agent TUI (MoSCoW MOS-N6 / V6 N213).

Production-usable hooks (not stubs):
- TTS: pyttsx3 → Windows SAPI (safe subprocess) → offline echo mock
- STT: speech_recognition+mic → ~/.superai/voice_in.txt → queue API
- Config: ~/.superai/voice.json (auto-speak, enabled, rate)
- Contract-shaped results for automation / JSON mode
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def _voice_dir() -> Path:
    p = Path.home() / ".superai"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _config_path() -> Path:
    return _voice_dir() / "voice.json"


def _inbox_path() -> Path:
    return _voice_dir() / "voice_in.txt"


def _outbox_path() -> Path:
    return _voice_dir() / "voice_out.txt"


def default_config() -> Dict[str, Any]:
    return {
        "enabled": True,
        "auto_speak_replies": False,
        "rate": 180,
        "volume": 1.0,
        "prefer_backend": "auto",  # auto|pyttsx3|sapi|mock
        "stt_timeout": 5.0,
        "max_speak_chars": 2000,
    }


def load_config() -> Dict[str, Any]:
    cfg = default_config()
    path = _config_path()
    if path.is_file():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                cfg.update(raw)
        except Exception:
            pass
    # env overrides
    if (os.getenv("SUPERAI_VOICE_AUTO") or "").lower() in {"1", "true", "yes"}:
        cfg["auto_speak_replies"] = True
    if (os.getenv("SUPERAI_VOICE_OFF") or "").lower() in {"1", "true", "yes"}:
        cfg["enabled"] = False
    return cfg


def save_config(updates: Dict[str, Any]) -> Dict[str, Any]:
    cfg = load_config()
    for k, v in (updates or {}).items():
        if v is not None:
            cfg[k] = v
    _config_path().write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return cfg


def _contract(data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from .spend_guard import ensure_public_result

        data.setdefault("ok", bool(data.get("ok", True)))
        return ensure_public_result(data, mock=data.get("mock"), ok=data.get("ok"))
    except Exception:
        data.setdefault("ok", True)
        data.setdefault("contract", "superai.result.v1")
        return data


def list_backends() -> Dict[str, Any]:
    """Probe available TTS/STT backends (offline-safe)."""
    tts: List[str] = []
    stt: List[str] = []
    try:
        import pyttsx3  # noqa: F401

        tts.append("pyttsx3")
    except Exception:
        pass
    if sys.platform == "win32":
        tts.append("sapi")
    tts.append("mock")  # always available (writes outbox)
    try:
        import speech_recognition  # noqa: F401

        stt.append("speech_recognition")
    except Exception:
        pass
    stt.append("file")  # always
    stt.append("queue")  # same as file via queue_voice_text
    return _contract(
        {
            "ok": True,
            "tts": tts,
            "stt": stt,
            "config": load_config(),
            "inbox": str(_inbox_path()),
            "outbox": str(_outbox_path()),
        }
    )


def status() -> Dict[str, Any]:
    cfg = load_config()
    backends = list_backends()
    return _contract(
        {
            "ok": True,
            "enabled": bool(cfg.get("enabled")),
            "auto_speak_replies": bool(cfg.get("auto_speak_replies")),
            "backends": {"tts": backends.get("tts"), "stt": backends.get("stt")},
            "inbox_exists": _inbox_path().is_file(),
            "commands": [
                "/listen [seconds]",
                "/speak [text]",
                "/voice status|on|off|auto on|auto off|queue <text>|backends",
            ],
        }
    )


def _speak_pyttsx3(text: str, rate: int, volume: float) -> Dict[str, Any]:
    import pyttsx3  # type: ignore

    engine = pyttsx3.init()
    try:
        engine.setProperty("rate", int(rate))
        engine.setProperty("volume", float(max(0.0, min(1.0, volume))))
    except Exception:
        pass
    engine.say(text)
    engine.runAndWait()
    return {"ok": True, "backend": "pyttsx3"}


def _speak_sapi(text: str) -> Dict[str, Any]:
    """Windows SAPI via PowerShell; text passed through a temp file (no injection)."""
    if sys.platform != "win32":
        return {"ok": False, "error": "not_windows"}
    with tempfile.NamedTemporaryFile(
        "w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        f.write(text)
        path = f.name
    try:
        # Read file in PS and Speak — avoid embedding user text in -Command string
        ps = (
            "Add-Type -AssemblyName System.Speech; "
            f"$t = Get-Content -Raw -LiteralPath '{path.replace(chr(39), chr(39)+chr(39))}'; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$s.Speak($t)"
        )
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            timeout=60,
            shell=False,
            text=True,
        )
        if proc.returncode != 0:
            return {
                "ok": False,
                "backend": "sapi",
                "error": (proc.stderr or proc.stdout or "sapi_failed")[:300],
            }
        return {"ok": True, "backend": "sapi"}
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


def _speak_mock(text: str) -> Dict[str, Any]:
    """Offline/mock TTS: write spoken text to outbox for tests and CI."""
    p = _outbox_path()
    p.write_text(text, encoding="utf-8")
    return {"ok": True, "backend": "mock", "path": str(p), "mock": True, "chars": len(text)}


def speak(
    text: str,
    *,
    force_backend: Optional[str] = None,
    allow_mock: bool = True,
) -> Dict[str, Any]:
    """
    Speak text via best available TTS backend.
    Empty text → ok with skipped=True (no error).
    """
    cfg = load_config()
    if not cfg.get("enabled", True):
        return _contract({"ok": False, "error": "voice_disabled", "enabled": False})

    max_c = int(cfg.get("max_speak_chars") or 2000)
    text = (text or "").strip()
    if not text:
        return _contract({"ok": True, "skipped": True, "reason": "empty_text"})
    text = text[:max_c]
    rate = int(cfg.get("rate") or 180)
    volume = float(cfg.get("volume") or 1.0)
    prefer = (force_backend or cfg.get("prefer_backend") or "auto").lower()

    order: List[str]
    if prefer in {"pyttsx3", "sapi", "mock"}:
        order = [prefer]
        if prefer != "mock" and allow_mock:
            order.append("mock")
    else:
        order = ["pyttsx3", "sapi"]
        if allow_mock:
            order.append("mock")

    errors: List[str] = []
    for backend in order:
        try:
            if backend == "pyttsx3":
                r = _speak_pyttsx3(text, rate, volume)
            elif backend == "sapi":
                r = _speak_sapi(text)
            elif backend == "mock":
                r = _speak_mock(text)
            else:
                continue
            if r.get("ok"):
                r["chars"] = len(text)
                r["preview"] = text[:120]
                return _contract(r)
            errors.append(f"{backend}:{r.get('error')}")
        except Exception as e:
            errors.append(f"{backend}:{e}")
            continue

    return _contract(
        {
            "ok": False,
            "error": "no_tts_backend",
            "errors": errors[:5],
            "text": text[:200],
            "stub": False,
            "hint": "pip install pyttsx3 (optional) or use Windows SAPI / mock outbox",
        }
    )


def queue_voice_text(text: str) -> Dict[str, Any]:
    """Write text for listen_once file backend (tests / automation / no mic)."""
    p = _inbox_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    body = text or ""
    p.write_text(body, encoding="utf-8")
    return _contract({"ok": True, "path": str(p), "chars": len(body), "backend": "queue"})


def listen_once(
    timeout: float = 5.0,
    *,
    prefer_file: bool = False,
    consume_file: bool = True,
) -> Dict[str, Any]:
    """
    Speech-to-text once.

    Order:
    1. If prefer_file or SUPERAI_VOICE_FILE=1 → inbox file
    2. speech_recognition + Microphone (optional)
    3. inbox file ~/.superai/voice_in.txt
    """
    cfg = load_config()
    if not cfg.get("enabled", True):
        return _contract({"ok": False, "error": "voice_disabled", "enabled": False})

    timeout = float(timeout if timeout is not None else cfg.get("stt_timeout") or 5.0)
    prefer_file = prefer_file or (os.getenv("SUPERAI_VOICE_FILE") or "").lower() in {
        "1",
        "true",
        "yes",
    }

    def _from_file() -> Optional[Dict[str, Any]]:
        p = _inbox_path()
        if not p.is_file():
            return None
        try:
            text = p.read_text(encoding="utf-8", errors="replace").strip()
        except Exception:
            return None
        if not text:
            return None
        if consume_file:
            try:
                p.write_text("", encoding="utf-8")
            except Exception:
                pass
        return {
            "ok": True,
            "text": text[:4000],
            "backend": "file",
            "path": str(p),
        }

    if prefer_file:
        hit = _from_file()
        if hit:
            return _contract(hit)

    mic_err = ""
    if not prefer_file:
        try:
            import speech_recognition as sr  # type: ignore

            r = sr.Recognizer()
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=0.3)
                audio = r.listen(source, timeout=timeout, phrase_time_limit=min(30.0, timeout + 10))
            try:
                text = r.recognize_google(audio)
            except Exception:
                # offline fallback if pocketsphinx installed
                try:
                    text = r.recognize_sphinx(audio)
                    return _contract(
                        {"ok": True, "text": str(text)[:4000], "backend": "sphinx"}
                    )
                except Exception as e2:
                    mic_err = str(e2)[:200]
                    raise
            return _contract(
                {"ok": True, "text": str(text)[:4000], "backend": "speech_recognition"}
            )
        except Exception as e:
            mic_err = str(e)[:200]

    hit = _from_file()
    if hit:
        if mic_err:
            hit["mic_error"] = mic_err
        return _contract(hit)

    return _contract(
        {
            "ok": False,
            "error": mic_err or "no_stt_backend",
            "stub": False,
            "hint": (
                "Write text via: superai voice queue \"…\"  or  "
                "python -c \"from core.voice_io import queue_voice_text; queue_voice_text('hi')\"  "
                "or install SpeechRecognition + pyaudio"
            ),
            "inbox": str(_inbox_path()),
        }
    )


def speak_reply(text: str, *, force: bool = False) -> Dict[str, Any]:
    """Speak agent reply when auto_speak_replies is on (or force=True)."""
    cfg = load_config()
    if not force and not cfg.get("auto_speak_replies"):
        return _contract({"ok": True, "skipped": True, "reason": "auto_speak_off"})
    return speak(text)


def handle_voice_slash(arg: str) -> Dict[str, Any]:
    """
    Parse /voice subcommands for TUI.
    status | on | off | auto on|off | queue <text> | backends | rate <n>
    """
    parts = (arg or "").strip().split(maxsplit=1)
    sub = (parts[0] if parts else "status").lower()
    rest = parts[1] if len(parts) > 1 else ""

    if sub in {"status", "st", ""}:
        return status()
    if sub in {"on", "enable"}:
        return _contract({"ok": True, "config": save_config({"enabled": True})})
    if sub in {"off", "disable"}:
        return _contract({"ok": True, "config": save_config({"enabled": False})})
    if sub == "auto":
        mode = rest.strip().lower()
        if mode in {"on", "1", "true", "yes"}:
            return _contract(
                {"ok": True, "config": save_config({"auto_speak_replies": True})}
            )
        if mode in {"off", "0", "false", "no"}:
            return _contract(
                {"ok": True, "config": save_config({"auto_speak_replies": False})}
            )
        return _contract({"ok": False, "error": "usage: /voice auto on|off"})
    if sub == "queue":
        return queue_voice_text(rest)
    if sub in {"backends", "backend"}:
        return list_backends()
    if sub == "rate":
        try:
            n = int(rest.strip())
            return _contract({"ok": True, "config": save_config({"rate": n})})
        except Exception:
            return _contract({"ok": False, "error": "usage: /voice rate <int>"})
    if sub == "speak":
        return speak(rest or "SuperAI ready.")
    if sub == "listen":
        try:
            t = float(rest.strip()) if rest.strip() else 5.0
        except Exception:
            t = 5.0
        return listen_once(timeout=t)
    return _contract(
        {
            "ok": False,
            "error": f"unknown_voice_cmd:{sub}",
            "usage": "status|on|off|auto on|off|queue <text>|backends|rate <n>|speak|listen",
        }
    )
