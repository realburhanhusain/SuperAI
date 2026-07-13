"""
Minimal CLI i18n (N30).
"""

from __future__ import annotations

import os
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "en": {
        "ready": "Ready.",
        "task_done": "Task completed successfully",
        "task_failed": "Task failed",
        "approval": "Approval required",
        "doctor_ok": "Doctor checks passed",
        "budget_exceeded": "Budget exceeded",
    },
    "es": {
        "ready": "Listo.",
        "task_done": "Tarea completada con éxito",
        "task_failed": "La tarea falló",
        "approval": "Se requiere aprobación",
        "doctor_ok": "Comprobaciones del doctor correctas",
        "budget_exceeded": "Presupuesto superado",
    },
    "fr": {
        "ready": "Prêt.",
        "task_done": "Tâche terminée avec succès",
        "task_failed": "Échec de la tâche",
        "approval": "Approbation requise",
        "doctor_ok": "Contrôles doctor OK",
        "budget_exceeded": "Budget dépassé",
    },
    "de": {
        "ready": "Bereit.",
        "task_done": "Aufgabe erfolgreich abgeschlossen",
        "task_failed": "Aufgabe fehlgeschlagen",
        "approval": "Genehmigung erforderlich",
        "doctor_ok": "Doctor-Checks bestanden",
        "budget_exceeded": "Budget überschritten",
    },
}


def get_lang() -> str:
    lang = (os.getenv("SUPERAI_LANG") or os.getenv("LANG") or "en")[:2].lower()
    return lang if lang in MESSAGES else "en"


def t(key: str, lang: str | None = None) -> str:
    lang = lang or get_lang()
    return MESSAGES.get(lang, MESSAGES["en"]).get(key) or MESSAGES["en"].get(key) or key
