"""
N215 expansion — native screen-reader / OS accessibility bridges.

Completes the former "not AT-SPI/VoiceOver" boundary with real OS backends:

| Platform | Backends |
|----------|----------|
| Windows  | SAPI.SpVoice (win32com/powershell), System.Speech, Narrator toast file, UIA live region file |
| macOS    | `say`, osascript VoiceOver-oriented speak |
| Linux    | speech-dispatcher (`spd-say`), espeak/espeak-ng, notify-send |

All backends degrade gracefully; pure tests mock subprocess.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


def native_state_path() -> Path:
    p = Path.home() / ".superai" / "tui" / "a11y_native.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def uia_live_region_path() -> Path:
    """
    Windows Narrator / UIA consumers can watch this UTF-16 LE friendly text file.
    Also used as a generic SR live region on all platforms.
    """
    p = Path.home() / ".superai" / "tui" / "uia_live_region.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


@dataclass
class NativeA11yConfig:
    enabled: bool = True
    prefer: str = "auto"  # auto | sapi | say | spd | espeak | file | off
    rate: int = 0  # SAPI rate -10..10
    volume: int = 100
    also_file: bool = True
    also_notify: bool = True
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]) -> "NativeA11yConfig":
        if not d or not isinstance(d, dict):
            return cls()
        return cls(
            enabled=bool(d.get("enabled", True)),
            prefer=str(d.get("prefer") or "auto"),
            rate=int(d.get("rate") or 0),
            volume=int(d.get("volume") or 100),
            also_file=bool(d.get("also_file", True)),
            also_notify=bool(d.get("also_notify", True)),
            updated_at=d.get("updated_at"),
        )


def load_native_config() -> NativeA11yConfig:
    path = native_state_path()
    if path.is_file():
        try:
            return NativeA11yConfig.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            pass
    return NativeA11yConfig()


def save_native_config(cfg: NativeA11yConfig) -> Path:
    cfg.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    path = native_state_path()
    path.write_text(json.dumps(cfg.to_dict(), indent=2), encoding="utf-8")
    return path


def detect_backends() -> Dict[str, Any]:
    """Probe available native SR/TTS backends on this host."""
    system = platform.system().lower()
    backends: Dict[str, Any] = {
        "system": system,
        "platform": sys.platform,
        "file_live_region": True,
        "path": str(uia_live_region_path()),
    }
    if system == "windows" or sys.platform == "win32":
        backends["sapi_powershell"] = True
        backends["sapi_win32com"] = _win32com_sapi_available()
        backends["system_speech"] = shutil.which("powershell") is not None
        backends["narrator_hint"] = (
            "Enable Narrator (Win+Ctrl+Enter); live region file updates are polled-friendly"
        )
    elif system == "darwin":
        backends["say"] = shutil.which("say") is not None
        backends["osascript"] = shutil.which("osascript") is not None
        backends["voiceover_hint"] = "Cmd+F5 toggles VoiceOver; `say` used for spoken output"
    else:
        backends["spd_say"] = shutil.which("spd-say") is not None
        backends["espeak"] = bool(shutil.which("espeak") or shutil.which("espeak-ng"))
        backends["notify_send"] = shutil.which("notify-send") is not None
        backends["speech_dispatcher"] = backends["spd_say"]
        backends["atspi_hint"] = (
            "Install speech-dispatcher or espeak; file live region for AT-SPI consumers"
        )
    return backends


def _win32com_sapi_available() -> bool:
    try:
        import win32com.client  # type: ignore

        _ = win32com.client
        return True
    except Exception:
        return False


def write_uia_live_region(text: str) -> Path:
    """Write SR-visible live region (UTF-8 + BOM optional for Windows tools)."""
    path = uia_live_region_path()
    body = (text or "").strip()
    # Single-line + newline for watchers; overwrite so "live region" changes
    content = body + "\n"
    path.write_text(content, encoding="utf-8")
    # Also UTF-16 LE for some Windows accessibility tools
    try:
        path.with_suffix(".utf16.txt").write_text(content, encoding="utf-16")
    except Exception:
        pass
    return path


def speak_windows_sapi(text: str, *, rate: int = 0, volume: int = 100) -> Dict[str, Any]:
    """Windows SAPI via win32com or PowerShell System.Speech."""
    text = (text or "").strip()
    if not text:
        return {"ok": False, "error": "empty", "backend": "sapi"}
    # Prefer win32com
    if _win32com_sapi_available():
        try:
            import win32com.client  # type: ignore

            voice = win32com.client.Dispatch("SAPI.SpVoice")
            voice.Rate = max(-10, min(10, int(rate)))
            voice.Volume = max(0, min(100, int(volume)))
            voice.Speak(text)
            return {"ok": True, "backend": "sapi_win32com", "chars": len(text)}
        except Exception as e:
            com_err = str(e)[:200]
    else:
        com_err = "win32com_unavailable"

    # PowerShell System.Speech
    ps = shutil.which("powershell") or shutil.which("pwsh")
    if not ps:
        return {"ok": False, "error": f"no_powershell ({com_err})", "backend": "sapi"}
    # Escape single quotes for PowerShell
    safe = text.replace("'", "''")[:500]
    script = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$s.Rate = {int(max(-10, min(10, rate)))}; "
        f"$s.Volume = {int(max(0, min(100, volume)))}; "
        f"$s.Speak('{safe}')"
    )
    try:
        proc = subprocess.run(
            [ps, "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return {
            "ok": proc.returncode == 0,
            "backend": "system_speech_powershell",
            "returncode": proc.returncode,
            "stderr": (proc.stderr or "")[:300],
            "com_fallback": com_err,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:200], "backend": "sapi"}


def speak_macos_say(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if not text:
        return {"ok": False, "error": "empty", "backend": "say"}
    say = shutil.which("say")
    if not say:
        return {"ok": False, "error": "say_not_found", "backend": "say"}
    try:
        proc = subprocess.run([say, text[:500]], capture_output=True, text=True, timeout=60)
        return {"ok": proc.returncode == 0, "backend": "say", "returncode": proc.returncode}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200], "backend": "say"}


def speak_macos_voiceover_hint(text: str) -> Dict[str, Any]:
    """Speak via say; optionally post a notification for VO users."""
    r = speak_macos_say(text)
    osa = shutil.which("osascript")
    if osa and text:
        safe = text.replace('"', '\\"')[:200]
        try:
            subprocess.run(
                [
                    osa,
                    "-e",
                    f'display notification "{safe}" with title "SuperAI"',
                ],
                capture_output=True,
                timeout=15,
            )
            r["notification"] = True
        except Exception:
            r["notification"] = False
    return r


def speak_linux_spd(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if not text:
        return {"ok": False, "error": "empty", "backend": "spd-say"}
    spd = shutil.which("spd-say")
    if not spd:
        return {"ok": False, "error": "spd-say_not_found", "backend": "spd-say"}
    try:
        proc = subprocess.run(
            [spd, "-w", text[:500]], capture_output=True, text=True, timeout=60
        )
        return {"ok": proc.returncode == 0, "backend": "spd-say", "returncode": proc.returncode}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200], "backend": "spd-say"}


def speak_linux_espeak(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if not text:
        return {"ok": False, "error": "empty", "backend": "espeak"}
    bin_ = shutil.which("espeak-ng") or shutil.which("espeak")
    if not bin_:
        return {"ok": False, "error": "espeak_not_found", "backend": "espeak"}
    try:
        proc = subprocess.run(
            [bin_, text[:500]], capture_output=True, text=True, timeout=60
        )
        return {"ok": proc.returncode == 0, "backend": bin_, "returncode": proc.returncode}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200], "backend": "espeak"}


def notify_linux(text: str) -> Dict[str, Any]:
    ns = shutil.which("notify-send")
    if not ns:
        return {"ok": False, "error": "notify-send_not_found"}
    try:
        proc = subprocess.run(
            [ns, "SuperAI", text[:200]], capture_output=True, text=True, timeout=15
        )
        return {"ok": proc.returncode == 0, "backend": "notify-send"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def announce_native(
    text: str,
    *,
    cfg: Optional[NativeA11yConfig] = None,
) -> Dict[str, Any]:
    """
    Speak / publish text via the best native backend for this OS.
    Always can fall back to file live region.
    """
    from .spend_guard import ensure_public_result

    cfg = cfg or load_native_config()
    text = (text or "").strip()
    if not text:
        return ensure_public_result({"ok": False, "error": "empty"}, ok=False)
    if not cfg.enabled or cfg.prefer == "off":
        path = write_uia_live_region(text) if cfg.also_file else None
        return ensure_public_result(
            {"ok": True, "backend": "file_only" if path else "disabled", "path": str(path) if path else None},
            ok=True,
        )

    results: List[Dict[str, Any]] = []
    prefer = (cfg.prefer or "auto").lower()
    system = platform.system().lower()

    def _try_chain(fns) -> Dict[str, Any]:
        last = {"ok": False, "error": "no_backend"}
        for fn in fns:
            try:
                last = fn()
            except Exception as e:
                last = {"ok": False, "error": str(e)[:200]}
            results.append(last)
            if last.get("ok"):
                return last
        return last

    spoken: Dict[str, Any]
    if prefer == "file":
        spoken = {"ok": True, "backend": "file"}
    elif prefer == "sapi" or (prefer == "auto" and sys.platform == "win32"):
        spoken = _try_chain(
            [
                lambda: speak_windows_sapi(text, rate=cfg.rate, volume=cfg.volume),
            ]
        )
    elif prefer == "say" or (prefer == "auto" and system == "darwin"):
        spoken = _try_chain(
            [
                lambda: speak_macos_voiceover_hint(text),
                lambda: speak_macos_say(text),
            ]
        )
    elif prefer in {"spd", "spd-say", "atspi"} or (
        prefer == "auto" and system == "linux"
    ):
        # AT-SPI D-Bus + speech-dispatcher chain
        def _atspi():
            try:
                from .tui_atspi import announce_atspi

                return announce_atspi(text)
            except Exception as e:
                return {"ok": False, "error": str(e)[:200], "backend": "atspi"}

        spoken = _try_chain(
            [
                _atspi,
                lambda: speak_linux_spd(text),
                lambda: speak_linux_espeak(text),
            ]
        )
    elif prefer == "espeak":
        spoken = speak_linux_espeak(text)
        results.append(spoken)
    else:
        # auto fallback by platform
        if sys.platform == "win32":
            spoken = speak_windows_sapi(text, rate=cfg.rate, volume=cfg.volume)
        elif system == "darwin":
            spoken = speak_macos_say(text)
        else:
            spoken = speak_linux_spd(text)
            if not spoken.get("ok"):
                spoken = speak_linux_espeak(text)
        results.append(spoken)

    path = None
    if cfg.also_file:
        path = write_uia_live_region(text)

    notify = None
    if cfg.also_notify and system == "linux":
        notify = notify_linux(text)

    ok = bool(spoken.get("ok") or path)
    return ensure_public_result(
        {
            "ok": ok,
            "text": text[:200],
            "spoken": spoken,
            "attempts": results[-5:],
            "live_region": str(path) if path else None,
            "notify": notify,
            "backends": detect_backends(),
            "prefer": prefer,
        },
        ok=ok,
    )


@dataclass
class NativeA11yBridge:
    cfg: NativeA11yConfig = field(default_factory=load_native_config)

    def status(self) -> Dict[str, Any]:
        from .spend_guard import ensure_public_result

        return ensure_public_result(
            {
                "ok": True,
                "config": self.cfg.to_dict(),
                "backends": detect_backends(),
                "live_region": str(uia_live_region_path()),
            },
            ok=True,
        )

    def enable(self, on: bool = True, *, persist: bool = True) -> Dict[str, Any]:
        from .spend_guard import ensure_public_result

        self.cfg.enabled = bool(on)
        if persist:
            save_native_config(self.cfg)
        return ensure_public_result(
            {"ok": True, "enabled": self.cfg.enabled, **self.status()}, ok=True
        )

    def set_prefer(self, backend: str, *, persist: bool = True) -> Dict[str, Any]:
        from .spend_guard import ensure_public_result

        self.cfg.prefer = (backend or "auto").lower()
        if persist:
            save_native_config(self.cfg)
        return ensure_public_result(
            {"ok": True, "prefer": self.cfg.prefer}, ok=True
        )

    def announce(self, text: str) -> Dict[str, Any]:
        return announce_native(text, cfg=self.cfg)


NATIVE_A11Y_HELP = """
### Native screen-reader bridges (N215)

| Command | Action |
|---------|--------|
| `/a11y native` | Backend probe + config |
| `/a11y native on\\|off` | Enable native bridge |
| `/a11y native prefer auto\\|sapi\\|say\\|spd\\|espeak\\|file` | Prefer backend |
| `/a11y native say <text>` | Speak via OS backend now |

| OS | Backend |
|----|---------|
| Windows | SAPI / System.Speech + UIA live region file (Narrator-friendly) |
| macOS | `say` + notification (VoiceOver users hear spoken output) |
| Linux | **AT-SPI2** (`org.a11y.Bus`) + FDO notifications + `spd-say` / espeak |

CLI: `superai a11y native|native-say|backends|atspi`
"""


def handle_native_a11y_slash(arg: str = "", *, bridge: Optional[NativeA11yBridge] = None) -> Dict[str, Any]:
    from .foundation_safety import tui_envelope

    br = bridge or NativeA11yBridge()
    parts = (arg or "").strip().split(maxsplit=1)
    sub = (parts[0] if parts else "status").lower()
    rest = parts[1] if len(parts) > 1 else ""

    if sub in {"", "status", "st", "backends"}:
        return tui_envelope({**br.status(), "handled": True})
    if sub in {"on", "enable"}:
        return tui_envelope({**br.enable(True), "handled": True})
    if sub in {"off", "disable"}:
        return tui_envelope({**br.enable(False), "handled": True})
    if sub in {"prefer"} and rest:
        return tui_envelope({**br.set_prefer(rest.strip().split()[0]), "handled": True})
    if sub in {"say", "speak", "announce"} and rest:
        return tui_envelope({**br.announce(rest), "handled": True})
    if sub in {"help", "?"}:
        return tui_envelope({"ok": True, "handled": True, "help": NATIVE_A11Y_HELP})
    # bare "native" with no sub → status
    if sub == "native":
        return tui_envelope({**br.status(), "handled": True})
    return tui_envelope(
        {
            "ok": False,
            "handled": True,
            "error": "unknown_native_subcommand",
            "help": "status|on|off|prefer <backend>|say <text>|help",
        },
        ok=False,
    )
