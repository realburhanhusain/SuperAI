"""
Voice I/O stubs / hooks (N18).

TTS: pyttsx3 or Windows SAPI if available.
STT: placeholder unless speech_recognition + mic available.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def speak(text: str) -> Dict[str, Any]:
    text = (text or "")[:500]
    try:
        import pyttsx3  # type: ignore

        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        return {"ok": True, "backend": "pyttsx3"}
    except Exception:
        pass
    # Windows PowerShell fallback
    try:
        import subprocess
        import sys

        if sys.platform == "win32":
            # avoid injection: pass via env not string concat of user text in shell
            safe = text.replace("'", " ")
            ps = (
                "Add-Type -AssemblyName System.Speech; "
                f"(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{safe}')"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True,
                timeout=30,
                shell=False,
            )
            return {"ok": True, "backend": "sapi"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e), "stub": True}
    return {"ok": False, "error": "no TTS backend", "stub": True, "text": text}


def listen_once(timeout: float = 5.0) -> Dict[str, Any]:
    try:
        import speech_recognition as sr  # type: ignore

        r = sr.Recognizer()
        with sr.Microphone() as source:
            audio = r.listen(source, timeout=timeout)
        text = r.recognize_google(audio)
        return {"ok": True, "text": text, "backend": "speech_recognition"}
    except Exception as e:  # noqa: BLE001
        return {
            "ok": False,
            "error": str(e),
            "stub": True,
            "hint": "pip install SpeechRecognition pyaudio (optional)",
        }
