"""
Parallel multi-CLI runner + live job registry for agentic dashboards.

Runs multiple external AI CLIs concurrently and persists job state so
terminal + web dashboards can show all workers in one view.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .external_cli import ExternalCLITool


@dataclass
class CLIJob:
    id: str
    cli: str
    prompt: str
    status: str = "queued"  # queued | running | done | failed | cancelled
    role: str = "worker"
    approved: bool = False
    dry_run: bool = False
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    duration_sec: float = 0.0
    exit_code: Optional[int] = None
    stdout_tail: str = ""
    stderr_tail: str = ""
    error: Optional[str] = None
    command: List[str] = field(default_factory=list)
    workflow_id: Optional[str] = None
    context_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CLIJob":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore
        return cls(**{k: v for k, v in d.items() if k in known})


class ParallelCLIManager:
    """
    Shared registry of CLI jobs + parallel execution.
    State file: ~/.superai/cli_jobs.json (read by dashboard / web).
    """

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or (Path.home() / ".superai" / "cli_jobs.json"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.jobs: Dict[str, CLIJob] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                for item in data.get("jobs") or []:
                    if isinstance(item, dict) and item.get("id"):
                        self.jobs[item["id"]] = CLIJob.from_dict(item)
            except (OSError, json.JSONDecodeError):
                self.jobs = {}

    def save(self) -> None:
        """Persist jobs under lock. Windows-safe atomic replace with retry."""
        with self._lock:
            self._save_unlocked()

    def _save_unlocked(self) -> None:
        """Caller must hold self._lock."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "jobs": [j.to_dict() for j in self.jobs.values()],
        }
        data = json.dumps(payload, indent=2, default=str)
        # Unique tmp avoids multi-process collision on a shared .tmp name
        tmp = self.path.with_name(
            f"{self.path.stem}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex[:8]}.tmp"
        )
        tmp.write_text(data, encoding="utf-8")
        last_err: Optional[BaseException] = None
        for attempt in range(10):
            try:
                os.replace(str(tmp), str(self.path))
                return
            except PermissionError as e:
                # Common on Windows when another reader/AV holds the target briefly
                last_err = e
                time.sleep(0.015 * (attempt + 1))
            except OSError as e:
                last_err = e
                time.sleep(0.015 * (attempt + 1))
        # Last resort: in-place write (not atomic) so registry still updates
        try:
            self.path.write_text(data, encoding="utf-8")
        except OSError:
            if last_err is not None:
                raise last_err
            raise
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass

    def _set_job_fields(self, jid: str, **fields: Any) -> None:
        """Mutate a job and persist, under lock."""
        with self._lock:
            job = self.jobs.get(jid)
            if not job:
                return
            for k, v in fields.items():
                if hasattr(job, k):
                    setattr(job, k, v)
            self._save_unlocked()

    def list_jobs(
        self,
        status: Optional[str] = None,
        workflow_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            items = list(self.jobs.values())
            if status:
                items = [j for j in items if j.status == status]
            if workflow_id:
                items = [j for j in items if j.workflow_id == workflow_id]
            items.sort(key=lambda j: j.started_at or 0, reverse=True)
            return [j.to_dict() for j in items[:limit]]

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            j = self.jobs.get(job_id)
            return j.to_dict() if j else None

    def snapshot_for_dashboard(self) -> Dict[str, Any]:
        """Compact view for terminal + web dashboards."""
        jobs = self.list_jobs(limit=40)
        running = [j for j in jobs if j.get("status") == "running"]
        queued = [j for j in jobs if j.get("status") == "queued"]
        done = [j for j in jobs if j.get("status") in {"done", "failed"}]
        by_workflow: Dict[str, List[Dict[str, Any]]] = {}
        for j in jobs:
            wid = j.get("workflow_id") or "adhoc"
            by_workflow.setdefault(wid, []).append(j)
        return {
            "running": running,
            "queued": queued,
            "recent_done": done[:15],
            "by_workflow": {
                k: {
                    "count": len(v),
                    "running": sum(1 for x in v if x.get("status") == "running"),
                    "done": sum(1 for x in v if x.get("status") == "done"),
                    "failed": sum(1 for x in v if x.get("status") == "failed"),
                    "jobs": v,
                }
                for k, v in by_workflow.items()
            },
            "totals": {
                "running": len(running),
                "queued": len(queued),
                "done": sum(1 for j in jobs if j.get("status") == "done"),
                "failed": sum(1 for j in jobs if j.get("status") == "failed"),
                "all": len(jobs),
            },
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    def clear_finished(self) -> int:
        with self._lock:
            before = len(self.jobs)
            self.jobs = {
                k: v
                for k, v in self.jobs.items()
                if v.status in {"queued", "running"}
            }
            removed = before - len(self.jobs)
            self._save_unlocked()
            return removed

    def run_parallel(
        self,
        work: List[Dict[str, Any]],
        *,
        max_workers: int = 4,
        auto_approve: bool = False,
        dry_run: bool = False,
        with_context: bool = True,
        workflow_id: Optional[str] = None,
        workflow_label: str = "parallel-cli",
    ) -> Dict[str, Any]:
        """
        work: list of {cli, prompt, role?}
        Runs CLIs concurrently; updates registry live for dashboard.
        """
        if not work:
            return {"ok": False, "error": "no work items", "jobs": []}

        wid = workflow_id or f"wf-{uuid.uuid4().hex[:10]}"
        job_ids: List[str] = []
        with self._lock:
            for item in work:
                jid = f"cli-{uuid.uuid4().hex[:10]}"
                job = CLIJob(
                    id=jid,
                    cli=str(item.get("cli") or item.get("name") or "unknown"),
                    prompt=str(item.get("prompt") or item.get("task") or ""),
                    role=str(item.get("role") or "worker"),
                    approved=bool(auto_approve),
                    dry_run=bool(dry_run),
                    workflow_id=wid,
                    status="queued",
                )
                self.jobs[jid] = job
                job_ids.append(jid)
            self._save_unlocked()

        def _run_one(jid: str) -> CLIJob:
            with self._lock:
                job = self.jobs[jid]
                job.status = "running"
                job.started_at = time.time()
                self._save_unlocked()
                # Snapshot immutable-ish fields for work outside lock
                cli_name = job.cli
                prompt = job.prompt
                started_at = job.started_at

            try:
                from .central_memory import inject_context, write_back

                # Always-on Memory Palace unless with_context=False
                orig_prompt = prompt
                ctx = inject_context(
                    orig_prompt,
                    prompt=orig_prompt,
                    use_memory=with_context,
                    metadata={"workflow_id": wid, "cli": cli_name, "job_id": jid},
                )
                prompt = ctx.get("prompt") or prompt
                ctx_id = ctx.get("context_id")

                tool = ExternalCLITool(
                    auto_approve=auto_approve or dry_run,
                    dry_run=dry_run,
                    with_context=with_context,
                    write_memory=True,
                )
                # If CLI not on PATH, force dry-run so parallel demos still work
                force_dry = False
                try:
                    from .external_cli import ExternalCLIRegistry

                    if cli_name not in ExternalCLIRegistry().available():
                        tool.dry_run = True
                        force_dry = True
                except Exception:
                    tool.dry_run = True
                    force_dry = True

                # Role from job for supervisor–worker framing
                role_name = "worker"
                with self._lock:
                    role_name = self.jobs[jid].role or "worker"

                env = tool.run(
                    cli_name,
                    prompt,
                    approve=auto_approve or tool.dry_run,
                    with_context=with_context,
                    write_memory=True,
                    role=role_name,
                    workflow_id=wid,
                    source="cli_pool",
                    task_type="coding",
                )
                finished_at = time.time()
                duration = round(finished_at - (started_at or finished_at), 3)
                stdout_tail = (env.stdout or "")[-2000:]
                stderr_tail = (env.stderr or "")[-1000:]
                if env.ok or tool.dry_run:
                    status = "done"
                    error = env.error
                    if tool.dry_run and not stdout_tail:
                        stdout_tail = (
                            f"[dry-run] {cli_name} would run with context={ctx_id}"
                        )
                else:
                    status = "failed"
                    error = env.error or env.stderr or f"exit {env.exit_code}"

                try:
                    write_back(
                        task=orig_prompt[:500],
                        source="cli_pool",
                        model_or_cli=f"cli:{cli_name}",
                        success=status == "done",
                        latency=duration,
                        output=stdout_tail,
                        error=error,
                        context_id=ctx_id,
                        task_type="coding",
                        tags=["cli_pool", cli_name, wid],
                        metadata={
                            "job_id": jid,
                            "workflow_id": wid,
                            "dry_run": force_dry,
                        },
                        use_memory=with_context,
                    )
                except Exception:
                    pass

                with self._lock:
                    job = self.jobs[jid]
                    job.context_id = ctx_id
                    job.dry_run = bool(job.dry_run or force_dry or tool.dry_run)
                    job.finished_at = finished_at
                    job.duration_sec = duration
                    job.exit_code = env.exit_code
                    job.stdout_tail = stdout_tail
                    job.stderr_tail = stderr_tail
                    job.command = list(env.command or [])
                    job.approved = env.approved
                    job.error = error
                    job.status = status
                    self._save_unlocked()
                    return job
            except Exception as e:  # noqa: BLE001
                finished_at = time.time()
                with self._lock:
                    job = self.jobs[jid]
                    job.status = "failed"
                    job.error = str(e)
                    job.finished_at = finished_at
                    if job.started_at:
                        job.duration_sec = round(finished_at - job.started_at, 3)
                    self._save_unlocked()
                    return job

        workers = max(1, min(max_workers, len(job_ids)))
        results: List[CLIJob] = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(_run_one, jid): jid for jid in job_ids}
            for fut in as_completed(futs):
                results.append(fut.result())

        done = [j for j in results if j.status == "done"]
        failed = [j for j in results if j.status == "failed"]
        out = {
            "ok": len(failed) == 0,
            "workflow_id": wid,
            "workflow_label": workflow_label,
            "max_workers": workers,
            "total": len(results),
            "succeeded": len(done),
            "failed": len(failed),
            "jobs": [j.to_dict() for j in results],
            "dashboard": self.snapshot_for_dashboard(),
            "central_memory": with_context,
        }
        try:
            from .central_memory import write_back_workflow

            task_hint = str(
                (work[0].get("prompt") or work[0].get("task") or workflow_label)
            )[:400]
            out["memory_write"] = write_back_workflow(
                task=task_hint,
                source="cli_pool",
                workflow_id=wid,
                succeeded=len(done),
                failed=len(failed),
                total=len(results),
                jobs=out["jobs"],
                use_memory=with_context,
            )
        except Exception:
            pass
        return out

    def run_agentic_parallel(
        self,
        task: str,
        clis: Optional[List[str]] = None,
        *,
        max_workers: int = 4,
        dry_run: bool = True,
        auto_approve: bool = False,
    ) -> Dict[str, Any]:
        """
        Agentic fan-out: multiple CLIs attack the same task in parallel,
        then return structured results for supervisor merge.
        """
        if not clis:
            try:
                from .external_cli import ExternalCLIRegistry

                found = ExternalCLIRegistry().available()
                clis = found[:4] if found else ["claude", "aider", "cursor", "gemini"]
            except Exception:
                clis = ["claude", "aider", "cursor", "gemini"]

        roles = ["architect", "implementer", "tester", "reviewer"]
        work = []
        for i, cli in enumerate(clis):
            role = roles[i % len(roles)]
            work.append(
                {
                    "cli": cli,
                    "role": role,
                    "prompt": (
                        f"You are the {role} worker in a SuperAI multi-CLI agentic workflow.\n"
                        f"Task: {task}\n"
                        f"Focus on the {role} perspective. Be concise and actionable."
                    ),
                }
            )

        result = self.run_parallel(
            work,
            max_workers=max_workers,
            auto_approve=auto_approve,
            dry_run=dry_run,
            with_context=True,  # central Memory Palace for all workers
            workflow_label="agentic-parallel",
        )

        # Supervisor merge of successful outputs (+ Memory Palace preface)
        parts = []
        for j in result.get("jobs") or []:
            if j.get("status") == "done":
                parts.append(
                    f"### {j.get('cli')} ({j.get('role')})\n{j.get('stdout_tail') or j.get('error') or ''}"
                )
        merged = None
        if parts:
            try:
                from .central_memory import memory_preface_for_llm, write_back_workflow
                from .model_caller import ModelCaller
                from .model_registry import ModelRegistry

                reg = ModelRegistry()
                names = [n for n in reg.list_all_models() if not str(n).startswith("cli:")]
                model = names[0] if names else "gpt-4o"
                blob = "\n\n".join(parts)[:12000]
                mem = memory_preface_for_llm(task)
                merge_prompt = (
                    f"Supervisor merge of parallel CLI workers for task:\n{task}\n\n"
                    f"{blob}\n\nProduce one coherent plan/result."
                )
                if mem:
                    merge_prompt = f"{mem}\n\n{merge_prompt}"
                merged = ModelCaller(use_mock=True, registry=reg).call(
                    model=model,
                    prompt=merge_prompt,
                )
                result["synthesis"] = {
                    "model": model,
                    "text": merged.get("response"),
                    "memory_injected": bool(mem),
                }
                write_back_workflow(
                    task=task,
                    source="cli_pool_agentic",
                    workflow_id=str(result.get("workflow_id") or ""),
                    succeeded=int(result.get("succeeded") or 0),
                    failed=int(result.get("failed") or 0),
                    total=int(result.get("total") or 0),
                    synthesis=str(merged.get("response") or "")[:2000],
                    jobs=result.get("jobs") or [],
                )
            except Exception as e:  # noqa: BLE001
                result["synthesis"] = {"error": str(e), "parts": len(parts)}
        else:
            result["synthesis"] = {"text": None, "note": "no successful CLI outputs"}

        try:
            from .audit_log import AuditLog

            AuditLog().record(
                "cli_parallel_agentic",
                {
                    "workflow_id": result.get("workflow_id"),
                    "clis": clis,
                    "succeeded": result.get("succeeded"),
                    "failed": result.get("failed"),
                },
            )
        except Exception:
            pass

        return result
