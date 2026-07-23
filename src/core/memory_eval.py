"""
Offline Memory Roadmap eval harness (post P1–P8).

Exercises knowledge graph, cognify, session, recall, ingest, ontology,
datasets, and turn capture **without live LLM or network**.

Disjoint from AGY scorecard hardening — only memory modules + this harness.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class EvalCase:
    id: str
    phase: str
    name: str
    ok: bool
    detail: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)


def _iso_env(tmp: Path) -> Dict[str, str]:
    mem = tmp / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    return {
        "SUPERAI_MOCK_MODE": "1",
        "SUPERAI_EMBEDDING_HASH": "1",
        "SUPERAI_MEMORY_BACKEND": "memory",
        "HOME": str(tmp),
        "USERPROFILE": str(tmp),
        "SUPERAI_KG_DSN": f"sqlite:///{(tmp / 'kg.sqlite').as_posix()}",
        "SUPERAI_SESSION_DSN": f"sqlite:///{(tmp / 'sessions.sqlite').as_posix()}",
        "SUPERAI_MEMORY_DSN": f"sqlite:///{(mem / 'palace.sqlite').as_posix()}",
        "SUPERAI_DATASETS_PATH": str(tmp / "datasets_registry.json"),
        "SUPERAI_DATASET_ID": "superai",
        "SUPERAI_CAPTURE_LEVEL": "session",
        "SUPERAI_DATASET_SCOPE": "on",
    }


def run_offline_memory_eval(
    *,
    tmp_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Run end-to-end offline checks for Memory Roadmap P1–P8.

    Returns a report with per-case results and overall ok.
    """
    cleanup = False
    if tmp_root is None:
        tmp_root = Path(tempfile.mkdtemp(prefix="superai_mem_eval_"))
        cleanup = False  # leave for inspection unless caller deletes

    env = _iso_env(tmp_root)
    old_env = {k: os.environ.get(k) for k in env}
    try:
        os.environ.update(env)
        cases = _run_cases(tmp_root)
    finally:
        for k, v in old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    passed = sum(1 for c in cases if c.ok)
    failed = [c for c in cases if not c.ok]
    report = {
        "ok": len(failed) == 0,
        "product": "memory_eval_offline",
        "tmp_root": str(tmp_root),
        "total": len(cases),
        "passed": passed,
        "failed": len(failed),
        "cases": [
            {
                "id": c.id,
                "phase": c.phase,
                "name": c.name,
                "ok": c.ok,
                "detail": c.detail,
                "evidence": c.evidence,
            }
            for c in cases
        ],
        "message": (
            f"Memory eval offline: {passed}/{len(cases)} passed"
            + (f"; failed={[c.id for c in failed]}" if failed else "")
        ),
    }
    return report


def _run_cases(tmp: Path) -> List[EvalCase]:
    cases: List[EvalCase] = []

    # P1 knowledge graph
    try:
        from core.knowledge_graph import KnowledgeGraph

        kg = KnowledgeGraph(lock_root=tmp)
        n1 = kg.upsert_node(name="Cloud SQL", type="System", dataset_id="superai")
        n2 = kg.upsert_node(name="Dataplex", type="System", dataset_id="superai")
        e = kg.upsert_edge(
            from_name="Cloud SQL",
            to_name="Dataplex",
            relation="USES",
            from_type="System",
            to_type="System",
            dataset_id="superai",
        )
        path = kg.path(from_name="Cloud SQL", to_name="Dataplex", hops=2, dataset_id="superai")
        ok = bool(n1.get("ok") and n2.get("ok") and e.get("ok") and path.get("found"))
        cases.append(
            EvalCase(
                "p1_kg",
                "P1",
                "knowledge graph upsert + path",
                ok,
                detail=str(path.get("message") or path.get("error") or "path ok"),
                evidence={"path_found": path.get("found"), "nodes": kg.status().get("nodes")},
            )
        )
    except Exception as ex:  # noqa: BLE001
        cases.append(EvalCase("p1_kg", "P1", "knowledge graph", False, str(ex)[:300]))

    # P2 cognify
    try:
        from core.cognify import cognify
        from core.knowledge_graph import KnowledgeGraph

        kg = KnowledgeGraph(lock_root=tmp)
        sample = "Banking App uses Cloud SQL.\nPolicy Tags protects Cloud SQL.\n"
        rep = cognify(
            sample,
            mode="mock",
            dry_run=False,
            store_palace=False,
            dataset_id="superai",
            kg=kg,
        )
        ok = bool(rep.get("ok") and int(rep.get("nodes_written") or 0) >= 1)
        cases.append(
            EvalCase(
                "p2_cognify",
                "P2",
                "cognify mock extract + graph write",
                ok,
                detail=str(rep.get("message") or ""),
                evidence={
                    "nodes_written": rep.get("nodes_written"),
                    "edges_written": rep.get("edges_written"),
                    "ontology_applied": rep.get("ontology_applied"),
                },
            )
        )
    except Exception as ex:  # noqa: BLE001
        cases.append(EvalCase("p2_cognify", "P2", "cognify", False, str(ex)[:300]))

    # P3 session
    try:
        from core.session_memory import SessionMemory

        sm = SessionMemory(lock_root=tmp)
        sid = "eval_sess_1"
        sm.start(session_id=sid, dataset_id="superai", title="eval")
        sm.remember(sid, "prefer dark mode", kind="preference", importance=0.8, pinned=True)
        rec = sm.recall(sid, query="dark")
        ok = bool(rec.get("ok") and int(rec.get("count") or 0) >= 1)
        cases.append(
            EvalCase(
                "p3_session",
                "P3",
                "session remember + recall",
                ok,
                detail=str(rec.get("message") or ""),
                evidence={"count": rec.get("count")},
            )
        )
    except Exception as ex:  # noqa: BLE001
        cases.append(EvalCase("p3_session", "P3", "session", False, str(ex)[:300]))

    # P4 recall router
    try:
        from core.knowledge_graph import KnowledgeGraph
        from core.memory_palace import MemoryPalace
        from core.recall_router import recall

        mp = MemoryPalace()
        mp.store(
            "Cloud SQL managed postgres unique_eval_token",
            metadata={"dataset_id": "superai"},
            tags=["dataset:superai"],
        )
        kg = KnowledgeGraph(lock_root=tmp)
        out = recall(
            "unique_eval_token",
            strategy="keyword",
            dataset_id="superai",
            palace=mp,
            kg=kg,
        )
        blob = " ".join(str(h.get("content") or "") for h in (out.get("hits") or []))
        ok = bool(out.get("ok") and "unique_eval_token" in blob)
        cases.append(
            EvalCase(
                "p4_recall",
                "P4",
                "multi-strategy recall keyword",
                ok,
                detail=f"strategy={out.get('strategy')} count={out.get('count')}",
                evidence={"strategy": out.get("strategy"), "count": out.get("count")},
            )
        )
    except Exception as ex:  # noqa: BLE001
        cases.append(EvalCase("p4_recall", "P4", "recall", False, str(ex)[:300]))

    # P5 ingest
    try:
        from core.ingest import ingest

        doc = tmp / "note.md"
        doc.write_text("# Eval\n\nCloud SQL uses Dataplex.\n", encoding="utf-8")
        # workspace jail: set workspace to tmp
        os.environ["SUPERAI_WORKSPACE"] = str(tmp)
        rep = ingest(
            str(doc),
            dataset_id="superai",
            store_palace=True,
            cognify=False,
            dry_run=False,
            enforce_jail=True,
        )
        ok = bool(rep.get("ok") and int(rep.get("chunks_written") or 0) >= 1)
        cases.append(
            EvalCase(
                "p5_ingest",
                "P5",
                "markdown ingest to palace",
                ok,
                detail=str(rep.get("message") or ""),
                evidence={"chunks": rep.get("chunks_written"), "formats": rep.get("formats")},
            )
        )
    except Exception as ex:  # noqa: BLE001
        cases.append(EvalCase("p5_ingest", "P5", "ingest", False, str(ex)[:300]))

    # P6 ontology
    try:
        from core.ontology import MemoryOntology, default_ontology_path

        ont = MemoryOntology.load(default_ontology_path())
        v = ont.validate()
        m = ont.resolve_type("service")
        ok = bool(v.get("ok") and m.get("type") == "System")
        cases.append(
            EvalCase(
                "p6_ontology",
                "P6",
                "ontology validate + map service→System",
                ok,
                detail=str(v.get("message") or ""),
                evidence={"map": m},
            )
        )
    except Exception as ex:  # noqa: BLE001
        cases.append(EvalCase("p6_ontology", "P6", "ontology", False, str(ex)[:300]))

    # P7 datasets isolation
    try:
        from core.memory_dataset import DatasetRegistry, filter_by_dataset, memory_dataset_id
        from core.memory_palace import MemoryPalace

        reg = DatasetRegistry(path=tmp / "datasets_registry.json")
        reg.create("scratch")
        reg.use("scratch")
        os.environ["SUPERAI_DATASET_ID"] = "scratch"
        mp = MemoryPalace()
        mp.store("SCRATCH_ONLY_TOKEN_zzz", metadata={"dataset_id": "scratch"})
        os.environ["SUPERAI_DATASET_ID"] = "personal"
        mp.store("PERSONAL_ONLY_TOKEN_zzz", metadata={"dataset_id": "personal"})
        all_m = mp.get_all_memories() or []
        only_scratch = filter_by_dataset(all_m, "scratch", include_shared=False)
        blob = " ".join(str(m.get("content") or "") for m in only_scratch)
        ok = "SCRATCH_ONLY_TOKEN_zzz" in blob and "PERSONAL_ONLY_TOKEN_zzz" not in blob
        cases.append(
            EvalCase(
                "p7_dataset",
                "P7",
                "dataset isolation filter",
                ok,
                detail=f"scratch_hits={len(only_scratch)}",
                evidence={"active": reg.get_active()},
            )
        )
    except Exception as ex:  # noqa: BLE001
        cases.append(EvalCase("p7_dataset", "P7", "dataset", False, str(ex)[:300]))

    # P8 capture stream
    try:
        from core.session_capture import process_turn_stream
        from core.session_memory import SessionMemory

        sm = SessionMemory(lock_root=tmp)
        out = process_turn_stream(
            [
                {"hook": "user_prompt", "content": "What is Cloud SQL?"},
                {"hook": "assistant_final", "content": "Managed Postgres service."},
            ],
            session_id="eval_capture",
            level="session",
            dataset_id="superai",
            sm=sm,
            auto_end=True,
        )
        ok = bool(out.get("ok") and int(out.get("items_count") or 0) >= 2)
        cases.append(
            EvalCase(
                "p8_capture",
                "P8",
                "turn capture stream",
                ok,
                detail=str(out.get("message") or ""),
                evidence={"items": out.get("items_count"), "level": out.get("level")},
            )
        )
    except Exception as ex:  # noqa: BLE001
        cases.append(EvalCase("p8_capture", "P8", "capture", False, str(ex)[:300]))

    return cases


def report_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Memory Roadmap Offline Eval",
        "",
        f"**Overall:** {'PASS' if report.get('ok') else 'FAIL'} "
        f"({report.get('passed')}/{report.get('total')})",
        f"**Workdir:** `{report.get('tmp_root')}`",
        "",
        "| ID | Phase | Name | Result | Detail |",
        "|----|-------|------|--------|--------|",
    ]
    for c in report.get("cases") or []:
        mark = "PASS" if c.get("ok") else "FAIL"
        detail = str(c.get("detail") or "").replace("|", "/").replace("\n", " ")[:80]
        lines.append(
            f"| `{c.get('id')}` | {c.get('phase')} | {c.get('name')} | **{mark}** | {detail} |"
        )
    lines.append("")
    lines.append(str(report.get("message") or ""))
    return "\n".join(lines)
