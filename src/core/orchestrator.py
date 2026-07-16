"""
SuperAI Orchestrator (Phase 1 foundation + Phase 2/3 + mid-task adaptation)

Guided by implementation_plan_v2 / detailed plan.
Stabilized wiring: registry → router → caller, structured results, history, logging.

Gap close (dynamic adaptation):
  - Per-step retry + failover chain + error_recovery classification
  - Replan remaining steps after hard failures
  - Mid-task memory/skills refresh via central Memory Palace
  - Simple quality gate + one rework pass
  - Mid-run budget check
  - Structured metadata.degraded for soft-fail optional components
  - Thread-safe context / cost accumulation under parallel batches
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from .config import Config
from .errors import OrchestratorError, UserInputError
from .history import TaskHistory
from .learning_engine import LearningEngine
from .load_balancer import LoadBalancer, parse_strategy
from .logger import get_logger
from .memory_palace import MemoryPalace
from .model_caller import ModelCaller
from .model_registry import ModelRegistry
from .model_router import ModelRouter
from .preferences import UserPreferenceModel
from .provider_health import ProviderHealthStore
from .skills import SkillsManager
from .hitl import HITLStore
from .step_cache import StepResultCache
from .task_planner import ExecutionStep, TaskPlanner
from .task_result import TaskResult

console = Console()
logger = get_logger("superai.orchestrator")


class SuperAIOrchestrator:
    """Main orchestration engine for SuperAI."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.model_registry = ModelRegistry()
        strategy = parse_strategy(self.config.get("load_balancing_strategy"))
        self.load_balancer = LoadBalancer(strategy=strategy)
        self.health_store = ProviderHealthStore()
        self.model_router = ModelRouter(
            self.model_registry,
            self.load_balancer,
            health_store=self.health_store,
        )
        self._soft(
            "history_stats",
            lambda: self.model_router.refresh_history_stats(),
        )
        self.model_caller = ModelCaller(
            use_mock=self.config.use_mock,
            registry=self.model_registry,
            load_balancer=self.load_balancer,
            health_store=self.health_store,
        )
        self.task_planner = TaskPlanner(
            self.model_router, model_caller=self.model_caller
        )
        self.memory_palace = MemoryPalace()
        self.learning_engine = LearningEngine(self.memory_palace)
        self.skills_manager = SkillsManager()
        self.history = TaskHistory()
        self.preferences = UserPreferenceModel()
        self._soft(
            "preferences",
            lambda: self.preferences.apply_to_config_defaults(self.config),
        )
        self._soft(
            "external_cli_models",
            lambda: self.model_registry.register_external_clis_as_models(),
        )
        self.step_cache = StepResultCache()
        self.hitl = HITLStore()
        self.use_step_cache = bool(self.config.get("use_step_cache", True))
        self._exec_lock = threading.RLock()
        self._degraded: List[Dict[str, str]] = []
        self._adaptation_events: List[Dict[str, Any]] = []
        logger.info(
            "SuperAIOrchestrator initialized (mock_mode=%s, strategy=%s)",
            self.config.use_mock,
            strategy.value,
        )

    # ── soft-fail helpers ──────────────────────────────────────────────

    def _soft(self, feature: str, fn, *, result: Optional[Dict] = None) -> Any:
        """Run optional side effect; record degradation instead of crashing."""
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            logger.warning("Optional feature '%s' degraded: %s", feature, e)
            entry = {"feature": feature, "error": str(e)[:300]}
            self._degraded.append(entry)
            if result is not None:
                result.setdefault("metadata", {}).setdefault("degraded", []).append(
                    entry
                )
            return None

    def _event(self, kind: str, **payload: Any) -> None:
        self._adaptation_events.append(
            {
                "ts": time.time(),
                "kind": kind,
                **payload,
            }
        )

    def run_task(
        self,
        task: str,
        forced_model: Optional[str] = None,
        verbose: bool = False,
        resume_task_id: Optional[str] = None,
        pause_on_clarification: bool = True,
        *,
        with_clis: Optional[List[str]] = None,
        cli_dry_run: bool = True,
        cli_approve: bool = False,
        critic_mode: Optional[str] = None,
        replan_requires_approval: Optional[bool] = None,
        workers: Optional[List[str]] = None,
        worker_prefer: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a task using planning, routing, adaptation, and model calls."""
        task = (task or "").strip()
        if not task:
            raise UserInputError(
                "Task description is empty.",
                hint='Provide a task, e.g. superai run "Create a FastAPI hello world"',
            )

        self._degraded = []
        # Per-run worker pool overrides (API models + CLIs)
        self._run_workers = workers
        self._run_worker_prefer = worker_prefer
        self._adaptation_events = []
        # Resolve overrides for this run
        if critic_mode is not None:
            self.config.config["critic_mode"] = str(critic_mode).lower()
        if replan_requires_approval is not None:
            self.config.config["replan_requires_approval"] = bool(
                replan_requires_approval
            )
        run_state_extra = {
            "council_used": 0,
            "with_clis": list(with_clis or []),
            "cli_dry_run": bool(cli_dry_run),
            "cli_approve": bool(cli_approve),
        }

        # Resume incomplete run
        resumed_completed: List[Dict[str, Any]] = []
        if resume_task_id:
            ck = self.step_cache.get_run(resume_task_id)
            if ck:
                task = ck.get("task") or task
                resumed_completed = list(ck.get("completed_steps") or [])
                task_id = resume_task_id
            else:
                task_id = resume_task_id
        else:
            task_id = self.history.new_task_id()

        started_at = datetime.now(timezone.utc).isoformat()
        start_time = time.time()

        # Block if vetoed
        if self.hitl.is_vetoed(task_id):
            return {
                "task_id": task_id,
                "task": task,
                "success": False,
                "status": "failed",
                "message": "Task vetoed by human",
                "error": "vetoed",
                "steps": resumed_completed,
            }

        # Optional pause when open clarifications exist (incl. replan approval)
        if pause_on_clarification:
            open_q = self.hitl.open_clarifications(task_id)
            if open_q:
                return {
                    "task_id": task_id,
                    "task": task,
                    "success": False,
                    "status": "waiting_human",
                    "message": "Paused: open clarification requests",
                    "clarifications": open_q,
                    "steps": resumed_completed,
                }

        # If a replan was approved while paused, prefer recovery steps on resume
        pending_replan_steps: Optional[List[ExecutionStep]] = None
        replan_dec = self.hitl.replan_decision(task_id)
        if (
            replan_dec
            and replan_dec.get("status") == "answered"
            and replan_dec.get("decision") == "approved"
            and not replan_dec.get("consumed")
        ):
            pending_replan_steps = self._steps_from_hitl_payload(
                (replan_dec.get("payload") or {}).get("steps") or []
            )
            if pending_replan_steps:
                self._event(
                    "replan_resume_approved",
                    clar_id=replan_dec.get("id"),
                    steps=[s.step_id for s in pending_replan_steps],
                )
                # mark consumed so we don't loop forever
                replan_dec["consumed"] = True
                try:
                    self.hitl.save()
                except Exception:  # noqa: BLE001
                    pass

        # S4 budget pre-check + N20 forecast (hard-stop when enforce_budget)
        forecast = None
        budget_guard = None
        enforce_budget = bool(self.config.get("enforce_budget", True))
        try:
            from .budget import BudgetGuard
            from .cost_forecast import forecast_task_cost

            forecast = forecast_task_cost(task, model=forced_model)
            budget_guard = BudgetGuard()
            budget_guard.configure(
                daily_usd=float(self.config.get("budget_daily_usd") or 5),
                run_usd=float(self.config.get("budget_run_usd") or 1),
                daily_tokens=int(self.config.get("budget_daily_tokens") or 500_000),
            )
            budget_guard.check_can_spend(
                estimated_usd=float(forecast.get("estimated_usd") or 0.01)
            )
        except RuntimeError:
            if enforce_budget:
                raise
            logger.warning("Budget exceeded but enforce_budget=false; continuing")
            self._degraded.append({"feature": "budget_soft", "error": "over_budget"})
            budget_guard = None
        except Exception as e:  # noqa: BLE001
            logger.warning("Budget/forecast degraded: %s", e)
            self._degraded.append({"feature": "budget_precheck", "error": str(e)[:300]})
            budget_guard = None

        # N21 A/B routing override
        if not forced_model:
            try:
                from .ab_routing import ABRouter

                ab = ABRouter().pick(self.model_router.classify_task(task))
                if ab:
                    forced_model = ab
                    self._event("ab_route", model=ab)
            except Exception as e:  # noqa: BLE001
                logger.warning("A/B routing degraded: %s", e)
                self._degraded.append({"feature": "ab_routing", "error": str(e)[:300]})

        task_type = self.model_router.classify_task(task)
        result: Dict[str, Any] = {
            "task_id": task_id,
            "task": task,
            "success": False,
            "status": "failed",
            "message": "",
            "model_used": None,
            "steps": [],
            "result": None,
            "error": None,
            "duration": 0.0,
            "mode": "mock" if self.config.use_mock else "live",
            "started_at": started_at,
            "finished_at": None,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
            "metadata": {
                "task_type": task_type,
                "strategy": self.load_balancer.strategy.value,
                "cost_forecast": forecast,
                "degraded": list(self._degraded),
                "adaptation_events": [],
            },
        }

        selected_model: Optional[str] = forced_model
        step_records: List[Dict[str, Any]] = []
        total_tokens = 0
        total_cost = 0.0
        run_state: Dict[str, Any] = {
            "context": "",
            "relevant_context": {},
            "skill_prompt_block": "",
            "skills": [],
            "total_tokens": 0,
            "total_cost": 0.0,
            "selected_model": selected_model,
            "replans_used": 0,
            "budget_guard": budget_guard,
            "council_used": 0,
            "with_clis": run_state_extra.get("with_clis") or [],
            "cli_dry_run": run_state_extra.get("cli_dry_run", True),
            "cli_approve": run_state_extra.get("cli_approve", False),
        }

        try:
            if verbose:
                console.print("[cyan]Creating execution plan...[/cyan]")
                explain = self.model_router.explain_selection(task, top_k=3)
                if explain:
                    console.print("[dim]Top routing candidates:[/dim]")
                    for row in explain:
                        console.print(
                            f"  [dim]{row['model']} score={row['score']} "
                            f"({row['provider']})[/dim]"
                        )
            logger.info("Starting task %s: %s", task_id, task)

            use_llm_plan = bool(self.config.get("prefer_llm_planner", True)) and (
                not self.config.use_mock
            )
            if pending_replan_steps:
                plan_steps = pending_replan_steps
                run_state["replans_used"] = max(
                    1, int(run_state.get("replans_used") or 0)
                )
            else:
                plan_steps = self.task_planner.create_plan(
                    task, use_llm=use_llm_plan or None
                )
            if resumed_completed:
                done_ids = {
                    int(s.get("step"))
                    for s in resumed_completed
                    if s.get("step") is not None
                }
                # On approved replan resume, keep completed history but run recovery steps
                if not pending_replan_steps:
                    plan_steps = [
                        s for s in plan_steps if s.step_id not in done_ids
                    ]
                step_records.extend(resumed_completed)
            if verbose:
                self.task_planner.print_plan(plan_steps)

            # Initial memory + skills (central Memory Palace when enabled)
            self._refresh_enrichment(
                task, task_type, run_state, result, verbose=verbose, reason="initial"
            )

            def _run_one_step(step: ExecutionStep) -> Dict[str, Any]:
                return self._execute_step_with_adaptation(
                    step=step,
                    task=task,
                    task_id=task_id,
                    task_type=task_type,
                    forced_model=forced_model,
                    run_state=run_state,
                    result=result,
                    verbose=verbose,
                )

            def _run_and_checkpoint(step: ExecutionStep) -> Dict[str, Any]:
                if self.hitl.is_vetoed(task_id):
                    rec = {
                        "step": step.step_id,
                        "description": step.description,
                        "status": "failed",
                        "error": "vetoed by human",
                        "result": None,
                        "model": None,
                        "duration_ms": 0,
                        "usage": {},
                        "estimated_cost_usd": 0.0,
                    }
                else:
                    rec = _run_one_step(step)
                with self._exec_lock:
                    step_records.append(rec)
                    snapshot = list(step_records)
                    done_ids = {
                        int(d["step"])
                        for d in snapshot
                        if d.get("step") is not None
                    }
                    remaining = [
                        s.step_id for s in plan_steps if s.step_id not in done_ids
                    ]
                self._soft(
                    "checkpoint",
                    lambda: self.step_cache.save_run_checkpoint(
                        task_id,
                        task,
                        completed_steps=snapshot,
                        remaining_step_ids=remaining,
                        metadata={"task_type": task_type},
                    ),
                    result=result,
                )
                # Mid-task learning + adaptive context (LearningEngine)
                if bool(self.config.get("mid_task_memory_refresh", True)):
                    try:
                        self.learning_engine.learn_from_step(
                            task_description=task,
                            step_id=int(step.step_id),
                            step_description=str(step.description),
                            task_type=task_type,
                            model_used=str(rec.get("model") or "unknown"),
                            success=rec.get("status") == "success",
                            output=str(rec.get("result") or "")[:800],
                            error=rec.get("error"),
                            latency=float(rec.get("duration_ms") or 0) / 1000.0,
                            task_id=task_id,
                        )
                    except Exception as e:  # noqa: BLE001
                        logger.warning("mid_task learn_from_step degraded: %s", e)
                        self._degraded.append(
                            {"feature": "mid_task_learn", "error": str(e)[:300]}
                        )
                        result.setdefault("metadata", {}).setdefault(
                            "degraded", []
                        ).append(
                            {"feature": "mid_task_learn", "error": str(e)[:300]}
                        )
                    # Collect live step outputs for adaptive context
                    with self._exec_lock:
                        buf = run_state.setdefault("live_step_outputs", [])
                        if rec.get("status") == "success" and rec.get("result"):
                            buf.append(str(rec.get("result"))[:500])
                        elif rec.get("error"):
                            buf.append(f"FAILED: {rec.get('error')}"[:400])
                    self._refresh_enrichment(
                        task,
                        task_type,
                        run_state,
                        result,
                        last_output=str(rec.get("result") or rec.get("error") or "")[
                            :800
                        ],
                        verbose=False,
                        reason=f"after_step_{step.step_id}",
                    )
                return rec

            # Adaptive execution: run plan; on hard failures, replan remaining
            max_replans = int(self.config.get("max_replans") or 0)
            if not bool(self.config.get("adapt_on_failure", True)):
                max_replans = 0

            while True:
                _new_records, parallel_meta = self._execute_plan_steps(
                    plan_steps,
                    _run_and_checkpoint,
                    verbose=verbose,
                    already_done={
                        int(s["step"])
                        for s in step_records
                        if s.get("step") is not None and s.get("status") == "success"
                    },
                )
                result["metadata"]["execution"] = parallel_meta

                failed_now = [
                    s
                    for s in step_records
                    if s.get("status") == "failed"
                    and not s.get("replanned_away")
                ]
                pending_ids = {
                    s.step_id
                    for s in plan_steps
                    if s.step_id
                    not in {
                        int(r["step"])
                        for r in step_records
                        if r.get("step") is not None
                    }
                }

                if (
                    failed_now
                    and run_state["replans_used"] < max_replans
                    and bool(self.config.get("adapt_on_failure", True))
                ):
                    new_steps = self._replan_after_failure(
                        task=task,
                        task_type=task_type,
                        failed_steps=failed_now,
                        completed_ok=[
                            s for s in step_records if s.get("status") == "success"
                        ],
                        plan_steps=plan_steps,
                        verbose=verbose,
                    )
                    if new_steps:
                        # Optional HITL approval before applying replan
                        decision = self._maybe_await_replan_approval(
                            task_id=task_id,
                            task=task,
                            new_steps=new_steps,
                            failed_now=failed_now,
                            step_records=step_records,
                            result=result,
                            verbose=verbose,
                        )
                        if decision == "waiting":
                            # Persist partial progress and stop for human
                            duration = time.time() - start_time
                            result.update(
                                {
                                    "success": False,
                                    "status": "waiting_human",
                                    "message": (
                                        "Paused: recovery replan awaits approval. "
                                        "Answer with: superai hitl answer <id> approve|reject "
                                        "then superai run --resume <task_id>"
                                    ),
                                    "model_used": run_state.get("selected_model")
                                    or selected_model,
                                    "steps": step_records,
                                    "duration": round(duration, 3),
                                    "finished_at": datetime.now(
                                        timezone.utc
                                    ).isoformat(),
                                }
                            )
                            result["metadata"]["adaptation_events"] = list(
                                self._adaptation_events
                            )
                            result["metadata"]["degraded"] = list(self._degraded)
                            result["metadata"]["replans_used"] = run_state[
                                "replans_used"
                            ]
                            try:
                                self.history.save(result)
                            except Exception:  # noqa: BLE001
                                pass
                            return result
                        if decision == "rejected":
                            self._event(
                                "replan_rejected",
                                attempt=run_state["replans_used"] + 1,
                            )
                            if verbose:
                                console.print(
                                    "[yellow]→ Recovery replan rejected by human[/yellow]"
                                )
                            break
                        # approved or not required
                        run_state["replans_used"] += 1
                        self._event(
                            "replan",
                            attempt=run_state["replans_used"],
                            new_steps=[s.step_id for s in new_steps],
                            after_failures=[s.get("step") for s in failed_now],
                            approved=decision == "approved"
                            or decision == "auto",
                        )
                        plan_steps = new_steps
                        if verbose:
                            console.print(
                                f"[yellow]→ Replanned remaining work "
                                f"(attempt {run_state['replans_used']}): "
                                f"{len(new_steps)} step(s)[/yellow]"
                            )
                        continue
                break

            # Order records
            by_id = {
                int(s["step"]): s
                for s in step_records
                if s.get("step") is not None
            }
            step_records = [by_id[k] for k in sorted(by_id.keys())]

            with self._exec_lock:
                total_tokens = int(run_state["total_tokens"])
                total_cost = float(run_state["total_cost"])
                selected_model = run_state.get("selected_model") or selected_model

            success_steps = [s for s in step_records if s["status"] == "success"]
            failed_steps = [s for s in step_records if s["status"] == "failed"]
            if len(success_steps) > 1:
                final_output = self._synthesize_results(task, success_steps)
            elif success_steps:
                final_output = success_steps[0]["result"]
            elif step_records:
                final_output = step_records[0]["result"]
            else:
                final_output = "No result generated."

            # Optional multi-CLI fan-out (agentic) after main plan
            cli_bundle = None
            if run_state.get("with_clis"):
                cli_bundle = self._run_with_clis(
                    task=task,
                    clis=list(run_state["with_clis"]),
                    dry_run=bool(run_state.get("cli_dry_run", True)),
                    approve=bool(run_state.get("cli_approve", False)),
                    verbose=verbose,
                )
                result["metadata"]["cli_parallel"] = {
                    "workflow_id": (cli_bundle or {}).get("workflow_id"),
                    "succeeded": (cli_bundle or {}).get("succeeded"),
                    "failed": (cli_bundle or {}).get("failed"),
                    "dry_run": run_state.get("cli_dry_run"),
                }
                synth = ((cli_bundle or {}).get("synthesis") or {}).get("text")
                if synth:
                    final_output = (
                        f"{final_output}\n\n--- Multi-CLI synthesis ---\n{synth}"
                    )
                    self._event(
                        "with_clis",
                        clis=run_state["with_clis"],
                        workflow_id=(cli_bundle or {}).get("workflow_id"),
                    )

            any_failed = bool(failed_steps)
            all_failed = bool(step_records) and len(failed_steps) == len(step_records)
            no_steps = not step_records
            if all_failed or no_steps:
                overall_status = "failed"
                overall_success = False
            elif any_failed:
                overall_status = "partial"
                overall_success = False
            else:
                overall_status = "success"
                overall_success = True

            duration = time.time() - start_time
            finished_at = datetime.now(timezone.utc).isoformat()
            error_summary = None
            if failed_steps:
                error_summary = "; ".join(
                    f"step {s['step']}: {s.get('error') or 'failed'}"
                    for s in failed_steps[:5]
                )

            result.update(
                {
                    "success": overall_success,
                    "ok": overall_success,
                    "status": overall_status,
                    "message": {
                        "success": "Task completed successfully",
                        "partial": "Task completed with step failures",
                        "failed": "Task failed",
                    }.get(overall_status, overall_status),
                    "model_used": selected_model,
                    "steps": step_records,
                    "result": final_output,
                    "error": error_summary,
                    "duration": round(duration, 3),
                    "finished_at": finished_at,
                    "total_tokens": total_tokens,
                    "tokens": total_tokens,
                    "estimated_cost_usd": round(total_cost, 6),
                    "mock": bool(self.config.use_mock),
                    "dry_run": bool(run_state.get("cli_dry_run")),
                    "metadata": {
                        **result.get("metadata", {}),
                        "task_type": task_type,
                        "steps_succeeded": len(success_steps),
                        "steps_failed": len(failed_steps),
                        "routing_top": self.model_router.explain_selection(
                            task, top_k=3
                        ),
                        "routing_explain": self.model_router.explain_selection(
                            task, top_k=5
                        ),
                        "load_balancer": self.load_balancer.stats_snapshot(),
                        "cost_forecast": forecast,
                        "degraded": list(self._degraded),
                        "adaptation_events": list(self._adaptation_events),
                        "replans_used": run_state["replans_used"],
                        "permission_mode": self.config.get("permission_mode"),
                        "run_profile": self.config.get("run_profile"),
                    },
                }
            )
            try:
                from .result_contract import apply_contract

                chain = []
                for s in step_records:
                    m = s.get("model")
                    if m and m not in chain:
                        chain.append(m)
                if selected_model and selected_model not in chain:
                    chain.insert(0, selected_model)
                result["model_chain"] = chain
                mem_ids = []
                mid = (result.get("metadata") or {}).get("learning_memory_id")
                if mid:
                    mem_ids.append(str(mid))
                apply_contract(
                    result,
                    mock=bool(self.config.use_mock),
                    dry_run=bool(run_state.get("cli_dry_run")),
                    members=chain,
                    ok=overall_success if overall_status != "partial" else False,
                )
                if overall_status == "partial":
                    result["status"] = "partial"
                    result["ok"] = False
                if mem_ids:
                    result["memory_ids"] = list(
                        dict.fromkeys((result.get("memory_ids") or []) + mem_ids)
                    )
            except Exception:
                result.setdefault("contract", "superai.result.v1")

            if verbose:
                color = "green" if overall_success else "yellow"
                console.print(
                    f"\n[bold {color}]Task {overall_status} in {duration:.2f}s "
                    f"({len(success_steps)} ok / {len(failed_steps)} failed)[/bold {color}]"
                )
                if self._degraded:
                    console.print(
                        f"[dim]Degraded features: "
                        f"{[d['feature'] for d in self._degraded]}[/dim]"
                    )

            # Phase 3: learn from outcome + central memory write-back
            def _learn():
                memory_id = self.learning_engine.learn_from_task(
                    task_description=task,
                    task_type=task_type,
                    model_used=selected_model or "unknown",
                    success=overall_success,
                    latency=duration,
                    cost=total_cost,
                    steps_completed=len(success_steps),
                    steps_failed=len(failed_steps),
                    error_message=error_summary,
                )
                result["metadata"]["learning_memory_id"] = memory_id
                try:
                    from .central_memory import write_back

                    wb = write_back(
                        task=task,
                        source="orchestrator",
                        model_or_cli=selected_model or "unknown",
                        success=overall_success,
                        latency=duration,
                        cost=total_cost,
                        output=str(final_output or "")[:2000],
                        error=error_summary,
                        task_type=task_type,
                        tags=["orchestrator", "run_task", task_type],
                        metadata={"task_id": task_id, "status": overall_status},
                    )
                    result["metadata"]["central_memory_write"] = wb
                except Exception as e:  # noqa: BLE001
                    raise e

            self._soft("learning", _learn, result=result)

            self._soft(
                "preferences_observe",
                lambda: self.preferences.observe_task(
                    task_type=task_type,
                    model=selected_model or "unknown",
                    success=overall_success,
                    duration=duration,
                ),
                result=result,
            )

            def _bandit():
                reward = self.model_router.update_bandit(
                    model=selected_model or "unknown",
                    success=overall_success,
                    latency=duration,
                    cost=total_cost,
                )
                if reward is not None:
                    result["metadata"]["bandit_reward"] = reward

            self._soft("bandit", _bandit, result=result)

            def _budget_record():
                from .budget import BudgetGuard

                BudgetGuard().record(usd=total_cost, tokens=total_tokens)

            self._soft("budget_record", _budget_record, result=result)

            def _audit():
                from .audit_log import AuditLog

                AuditLog().record(
                    "run_task",
                    {
                        "task_id": task_id,
                        "success": overall_success,
                        "model": selected_model,
                        "cost": total_cost,
                        "replans": run_state["replans_used"],
                    },
                    outcome="ok" if overall_success else "fail",
                )

            self._soft("audit", _audit, result=result)

            def _telemetry():
                from .telemetry import Telemetry

                Telemetry().event(
                    "run_task",
                    {
                        "status": overall_status,
                        "success": overall_success,
                        "model": selected_model,
                        "duration": duration,
                        "task_type": task_type,
                    },
                )

            self._soft("telemetry", _telemetry, result=result)

            def _skill_outcomes():
                for sname in result.get("metadata", {}).get("skills") or []:
                    self.skills_manager.record_outcome(
                        sname, success=overall_success
                    )

            self._soft("skill_outcomes", _skill_outcomes, result=result)

            if overall_success:
                def _auto_skills():
                    created = self._maybe_auto_create_skills(
                        task_type, min_success_count=3
                    )
                    if created:
                        result["metadata"]["skills_created"] = created
                        for cname in created:
                            self.skills_manager.sandbox_skill(cname)
                        if verbose:
                            console.print(
                                f"[green]→ Auto-created skills (sandbox): {created}[/green]"
                            )

                self._soft("auto_skills", _auto_skills, result=result)
                self._soft(
                    "clear_checkpoint",
                    lambda: self.step_cache.clear_run(task_id),
                    result=result,
                )
                def _patterns():
                    from .pattern_extract import PatternExtractor

                    patterns = PatternExtractor().extract(min_support=3)
                    if patterns.get("type_patterns"):
                        result["metadata"]["patterns"] = patterns["type_patterns"][:5]

                self._soft("pattern_extract", _patterns, result=result)

            logger.info(
                "Task %s finished status=%s duration=%.2fs degraded=%s events=%s",
                task_id,
                result["status"],
                duration,
                len(self._degraded),
                len(self._adaptation_events),
            )

        except UserInputError:
            raise
        except Exception as e:  # noqa: BLE001
            duration = time.time() - start_time
            result.update(
                {
                    "success": False,
                    "status": "failed",
                    "message": f"Orchestration failed: {e}",
                    "error": str(e),
                    "duration": round(duration, 3),
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "steps": step_records,
                    "model_used": selected_model,
                }
            )
            result.setdefault("metadata", {})["degraded"] = list(self._degraded)
            result["metadata"]["adaptation_events"] = list(self._adaptation_events)
            logger.exception("Task %s failed", task_id)
            raise OrchestratorError(str(e)) from e
        finally:
            try:
                self.history.save(result)
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to persist history: %s", e)
                self._degraded.append(
                    {"feature": "history_save", "error": str(e)[:300]}
                )
                result.setdefault("metadata", {}).setdefault("degraded", []).append(
                    {"feature": "history_save", "error": str(e)[:300]}
                )

        try:
            typed = TaskResult.from_dict(result).to_dict()
            if typed:
                result.setdefault("metadata", {})["task_result_validated"] = True
        except Exception as e:  # noqa: BLE001
            logger.debug("TaskResult validation skipped: %s", e)
            self._degraded.append(
                {"feature": "task_result_validate", "error": str(e)[:200]}
            )

        result.setdefault("metadata", {})["degraded"] = list(self._degraded)
        result["metadata"]["adaptation_events"] = list(self._adaptation_events)
        return result

    # ── mid-task enrichment ────────────────────────────────────────────

    def _refresh_enrichment(
        self,
        task: str,
        task_type: str,
        run_state: Dict[str, Any],
        result: Dict[str, Any],
        last_output: str = "",
        verbose: bool = False,
        reason: str = "",
    ) -> None:
        """Refresh Memory Palace learnings + skills (mid-task adaptation)."""

        def _mem():
            live = list(run_state.get("live_step_outputs") or [])
            if last_output and (
                not live or live[-1] != last_output[:500]
            ):
                live = live + [last_output[:500]]
            # Dynamic mid-task context from LearningEngine
            if reason and reason != "initial":
                ctx = self.learning_engine.refresh_context_mid_task(
                    task,
                    task_type=task_type,
                    recent_step_outputs=live,
                    limit=6,
                )
            else:
                ctx = self.learning_engine.get_relevant_context_for_current_task(
                    task_description=task,
                    task_type=task_type,
                    limit=5,
                )
            try:
                from .central_memory import memory_preface_for_llm

                preface = memory_preface_for_llm(
                    task if not last_output else f"{task}\n{last_output[:200]}",
                    top_k=4,
                )
                if preface:
                    ctx.setdefault("relevant_learnings", []).insert(
                        0, {"content": preface, "id": "central_preface"}
                    )
            except Exception:
                pass
            with self._exec_lock:
                run_state["relevant_context"] = ctx
                run_state["live_step_outputs"] = live[-12:]
            return ctx

        def _skills():
            skills = self.skills_manager.get_relevant_skills(task, top_k=3)
            block = ""
            if skills:
                block = self.skills_manager.format_for_prompt(skills)
                for s in skills:
                    try:
                        self.skills_manager.mark_used(s["name"])
                    except Exception:  # noqa: BLE001
                        pass
            with self._exec_lock:
                run_state["skills"] = skills
                run_state["skill_prompt_block"] = block
            result["metadata"]["skills"] = [s.get("name") for s in skills]
            result["metadata"]["skills_injected"] = bool(skills)
            return skills

        self._soft(f"memory_refresh:{reason}", _mem, result=result)
        self._soft(f"skills_refresh:{reason}", _skills, result=result)
        if reason and reason != "initial":
            self._event("enrichment_refresh", reason=reason)
        if verbose and run_state.get("relevant_context"):
            console.print("[yellow]→ Using past learnings for this task[/yellow]")
        if verbose and run_state.get("skills"):
            console.print(
                f"[dim]→ Injecting skills: "
                f"{[s.get('name') for s in run_state['skills']]}[/dim]"
            )

    # ── step execution with retry / failover / quality ─────────────────

    def _effective_worker_prefer(self) -> str:
        """Resolve worker_prefer for this run (CLI flag > config > legacy)."""
        override = getattr(self, "_run_worker_prefer", None)
        if override:
            p = str(override).lower().strip()
            return p if p in {"mixed", "api", "cli", "router", "off"} else "mixed"
        # Legacy: cli_delegate_workers ⇒ CLI-first worker pool (unless run overrides)
        if bool(self.config.get("cli_delegate_workers", False)):
            return "cli"
        pref = str(self.config.get("worker_prefer") or "mixed").lower().strip()
        if pref not in {"mixed", "api", "cli", "router", "off"}:
            return "mixed"
        return pref

    def _configured_worker_members(self) -> Optional[List[str]]:
        run_w = getattr(self, "_run_workers", None)
        if run_w:
            return [str(x).strip() for x in run_w if str(x).strip()]
        raw = self.config.get("worker_members")
        if raw is None or raw == "" or raw == []:
            return None
        if isinstance(raw, (list, tuple)):
            return [str(x).strip() for x in raw if str(x).strip()]
        return [p.strip() for p in str(raw).split(",") if p.strip()]

    def _worker_role_for_step(self, role: str) -> str:
        r = (role or "worker").lower()
        if r in {"worker", "implementer"}:
            return "implementer"
        if r in {"tester", "test"}:
            return "tester"
        if r in {"reviewer", "critic"}:
            return "reviewer"
        if r in {"advisor", "architect", "supervisor"}:
            return r if r != "supervisor" else "advisor"
        return "implementer"

    def _resolve_worker_pool(
        self,
        *,
        role: str,
        step_desc: str,
        forced_model: Optional[str],
        router_primary: Optional[str],
    ) -> List[str]:
        """Ordered primary + failover: API models and CLIs (cli:name@MODEL)."""
        from .member_selection import resolve_worker_pool

        prefer = self._effective_worker_prefer()
        max_n = max(1, int(self.config.get("worker_max") or 5))
        members = self._configured_worker_members()

        # Preferred CLI prepended into explicit list when set
        pref_cli = self.config.get("cli_delegate_preferred")
        if pref_cli:
            tag = (
                str(pref_cli)
                if str(pref_cli).startswith("cli:")
                else f"cli:{pref_cli}"
            )
            if members is None and prefer in {"cli", "mixed"}:
                members = [tag]
            elif members is not None and tag not in members:
                members = [tag] + list(members)

        # Profile: local-only / prefer open-weight — seed members from catalog
        if members is None and (
            self.config.get("local_only")
            or self.config.get("prefer_local")
            or self.config.get("prefer_open_weight")
        ):
            try:
                from .member_selection import list_selectable_members

                data = list_selectable_members(
                    only_available=True,
                    with_cli_models=False,
                    open_weight=True
                    if self.config.get("prefer_open_weight")
                    or self.config.get("prefer_local")
                    or self.config.get("local_only")
                    else None,
                    local_only=bool(self.config.get("local_only")),
                    include_ollama_live=bool(
                        self.config.get("auto_ollama_discover")
                    ),
                )
                ids = [
                    m["id"]
                    for m in (data.get("api_models") or [])
                    if m.get("available")
                ]
                if ids:
                    members = ids[:max_n]
                    if self.config.get("local_only") or self.config.get(
                        "prefer_local"
                    ):
                        prefer = "api"
            except Exception:
                pass

        router_failover = self._failover_candidates_router(
            router_primary or forced_model, step_desc
        )
        pool = resolve_worker_pool(
            members,
            prefer=prefer,
            role=self._worker_role_for_step(role),
            max_members=max_n,
            forced_primary=forced_model,
            router_primary=router_primary,
            router_failover=router_failover,
        )
        return pool

    def _failover_candidates_router(
        self, primary: Optional[str], step_desc: str
    ) -> List[str]:
        """Classic router/registry failover (API-leaning); used inside worker pool."""
        names: List[str] = []
        chain = list(self.config.get("failover_chain") or [])
        for n in chain:
            if n and n not in names and n != primary:
                names.append(str(n))
        try:
            for row in self.model_router.explain_selection(step_desc, top_k=5) or []:
                m = row.get("model")
                if m and m not in names and m != primary:
                    names.append(str(m))
        except Exception:  # noqa: BLE001
            pass
        try:
            for m in self.model_registry.list_all_models() or []:
                sm = str(m)
                if sm not in names and sm != primary:
                    names.append(sm)
                if len(names) >= 6:
                    break
        except Exception:  # noqa: BLE001
            pass
        return names[:6]

    def _failover_candidates(
        self, primary: Optional[str], step_desc: str
    ) -> List[str]:
        """Backward-compatible failover list (router + unified worker extras)."""
        return self._failover_candidates_router(primary, step_desc)

    def _quality_ok(self, text: Any) -> Tuple[bool, str]:
        """Lightweight quality gate — fail empty/error-like outputs."""
        if not bool(self.config.get("quality_gate", True)):
            return True, "disabled"
        s = str(text or "").strip()
        if not s:
            return False, "empty_output"
        if s.lower().startswith("error:"):
            return False, "error_prefix"
        if len(s) < 8:
            return False, "too_short"
        bad = ("traceback (most recent call last)", "exception:", "fatal:")
        low = s.lower()
        if any(b in low for b in bad):
            return False, "looks_like_exception"
        return True, "ok"

    def _execute_step_with_adaptation(
        self,
        step: ExecutionStep,
        task: str,
        task_id: str,
        task_type: str,
        forced_model: Optional[str],
        run_state: Dict[str, Any],
        result: Dict[str, Any],
        verbose: bool,
    ) -> Dict[str, Any]:
        from .error_recovery import classify_error

        if verbose:
            console.print(
                f"\n[bold blue]Step {step.step_id}:[/bold blue] {step.description}"
            )

        if self.hitl.is_vetoed(task_id):
            return {
                "step": step.step_id,
                "description": step.description,
                "model": None,
                "status": "failed",
                "result": None,
                "error": "vetoed by human",
                "duration_ms": 0,
                "usage": {},
                "estimated_cost_usd": 0.0,
            }

        # Mid-run budget check
        bg = run_state.get("budget_guard")
        if bg is not None:
            try:
                spent = float(run_state.get("total_cost") or 0)
                bg.check_can_spend(estimated_usd=max(0.001, spent * 0.05 + 0.001))
            except RuntimeError as e:
                self._event("budget_stop", step=step.step_id, error=str(e))
                return {
                    "step": step.step_id,
                    "description": step.description,
                    "model": None,
                    "status": "failed",
                    "result": None,
                    "error": f"budget: {e}",
                    "duration_ms": 0,
                    "usage": {},
                    "estimated_cost_usd": 0.0,
                    "recovery": classify_error(e),
                }
            except Exception as e:  # noqa: BLE001
                logger.warning("Mid-run budget check degraded: %s", e)
                self._degraded.append(
                    {"feature": "budget_mid_run", "error": str(e)[:300]}
                )
                result.setdefault("metadata", {}).setdefault("degraded", []).append(
                    {"feature": "budget_mid_run", "error": str(e)[:300]}
                )

        role = getattr(step, "role", "worker") or "worker"
        # Router suggestion (used when worker_prefer=router or as pool seed)
        preferred = (
            self.config.default_supervisor
            if role in {"supervisor", "critic"}
            else None
        ) or self.preferences.preferred_model_for(task_type)
        if role == "critic" and not preferred:
            preferred = self.config.default_supervisor
        router_primary = None
        if not forced_model:
            try:
                router_primary = self.model_router.select_model(
                    task_description=step.description,
                    preferred_model=preferred,
                    verbose=verbose,
                )
            except Exception:  # noqa: BLE001
                router_primary = preferred or "gpt-4o"

        # Unified worker pool for worker/implementer/tester (API + CLIs).
        # Supervisor/critic keep router primary unless --model forced.
        wprefer = self._effective_worker_prefer()
        worker_roles = {"worker", "implementer", "tester"}
        if forced_model or role in worker_roles:
            pool = self._resolve_worker_pool(
                role=role,
                step_desc=step.description,
                forced_model=forced_model,
                router_primary=router_primary,
            )
        else:
            pool = [router_primary or preferred or "gpt-4o"]
            pool.extend(
                self._failover_candidates_router(pool[0], step.description)
            )

        models_to_try: List[str] = []
        for m in pool:
            sm = str(m).strip() if m else ""
            if sm and sm not in models_to_try:
                models_to_try.append(sm)
        if not models_to_try:
            models_to_try = [forced_model or router_primary or "gpt-4o"]
        primary = models_to_try[0]

        if str(primary).startswith("cli:"):
            self._event(
                "cli_delegate",
                step=step.step_id,
                role=role,
                cli=str(primary),
                worker_prefer=wprefer,
            )
        self._event(
            "worker_pool",
            step=step.step_id,
            role=role,
            primary=primary,
            pool=models_to_try[:8],
            worker_prefer=wprefer,
        )
        if verbose and role in worker_roles:
            console.print(
                f"[cyan]→ Worker pool ({wprefer}): {', '.join(models_to_try[:6])}"
                f"{'…' if len(models_to_try) > 6 else ''}[/cyan]"
            )
        max_retries = max(0, int(self.config.get("max_step_retries") or 0))
        backoff = float(self.config.get("step_retry_backoff_sec") or 0.05)
        adapt = bool(self.config.get("adapt_on_failure", True))

        # Cache hit (primary only)
        if self.use_step_cache:
            cached = self.step_cache.get(step.description, primary)
            if cached and cached.get("status") == "success":
                if verbose:
                    console.print(f"[dim]→ Cache hit for step {step.step_id}[/dim]")
                with self._exec_lock:
                    run_state["context"] += (
                        f"\n\n[Step {step.step_id} Result]:\n"
                        f"{str(cached.get('result'))[:500]}..."
                    )
                return {
                    **cached,
                    "step": step.step_id,
                    "description": step.description,
                    "model": primary,
                    "cached": True,
                }

        step_start = time.time()
        last_error: Optional[str] = None
        last_recovery: Optional[Dict[str, Any]] = None
        last_output: Any = None
        last_usage: Dict[str, Any] = {}
        last_cost = 0.0
        last_model = primary
        attempts_log: List[Dict[str, Any]] = []

        for model in models_to_try:
            attempts = 1 + (max_retries if adapt else 0)
            for attempt in range(1, attempts + 1):
                last_model = model
                if verbose:
                    console.print(
                        f"[green]→ Using model: {model} "
                        f"(attempt {attempt}/{attempts})[/green]"
                    )
                try:
                    prompt = self._build_step_prompt(step, task, run_state)
                    call_result = self.model_caller.call(model=model, prompt=prompt)
                    step_output = self._extract_response_text(call_result)
                    usage: Dict[str, Any] = {}
                    cost = 0.0
                    status_err = None
                    if isinstance(call_result, dict):
                        usage = call_result.get("usage") or {}
                        cost = float(call_result.get("estimated_cost_usd") or 0.0)
                        if call_result.get("status") == "error":
                            status_err = str(
                                call_result.get("response") or "provider error"
                            )

                    if status_err:
                        raise RuntimeError(status_err)

                    ok, reason = self._quality_ok(step_output)
                    critic = str(
                        self.config.get("critic_mode") or "light"
                    ).lower()
                    if critic == "off":
                        ok, reason = True, "critic_off"

                    if not ok and adapt and critic in {"light", "council"}:
                        self._event(
                            "quality_retry",
                            step=step.step_id,
                            model=model,
                            reason=reason,
                            attempt=attempt,
                        )
                        # Light rework prompt
                        rework = (
                            f"Previous output failed quality gate ({reason}). "
                            f"Improve and complete:\n{step.description}\n\n"
                            f"Draft:\n{str(step_output)[:1500]}"
                        )
                        call_result = self.model_caller.call(
                            model=model,
                            prompt=rework + "\n\n" + prompt[:2000],
                        )
                        step_output = self._extract_response_text(call_result)
                        ok, reason = self._quality_ok(step_output)
                        if isinstance(call_result, dict):
                            usage = call_result.get("usage") or usage
                            cost = float(
                                call_result.get("estimated_cost_usd") or cost
                            )
                        # Optional multi-CLI reviewer board on light critic
                        if (
                            not ok
                            and critic == "light"
                            and bool(self.config.get("cli_delegate_reviewers", False))
                        ):
                            improved, cmeta = self._council_critique_step(
                                step=step,
                                draft=str(step_output or ""),
                                task=task,
                            )
                            if improved:
                                step_output = improved
                                ok, reason = self._quality_ok(step_output)
                                self._event(
                                    "cli_reviewer_board",
                                    step=step.step_id,
                                    **(cmeta or {}),
                                )

                    # Council critic: high complexity or still failing quality
                    complexity = (
                        getattr(step, "estimated_complexity", "") or ""
                    ).lower()
                    need_council = critic == "council" and (
                        complexity == "high"
                        or not ok
                        or "architect" in (step.description or "").lower()
                    )
                    max_c = int(self.config.get("council_max_per_run") or 1)
                    if (
                        need_council
                        and adapt
                        and int(run_state.get("council_used") or 0) < max_c
                    ):
                        improved, cmeta = self._council_critique_step(
                            step=step,
                            draft=str(step_output or ""),
                            task=task,
                        )
                        run_state["council_used"] = int(
                            run_state.get("council_used") or 0
                        ) + 1
                        if improved:
                            step_output = improved
                            ok, reason = self._quality_ok(step_output)
                            self._event(
                                "council_critic",
                                step=step.step_id,
                                **(cmeta or {}),
                            )

                    if critic != "off" and not ok:
                        raise RuntimeError(f"quality_gate:{reason}")

                    # Success
                    with self._exec_lock:
                        run_state["total_tokens"] += int(
                            usage.get("total_tokens") or 0
                        )
                        run_state["total_cost"] += cost
                        run_state["selected_model"] = model
                        run_state["context"] += (
                            f"\n\n[Step {step.step_id} Result]:\n"
                            f"{str(step_output)[:500]}..."
                        )

                    rec = {
                        "step": step.step_id,
                        "description": step.description,
                        "model": model,
                        "status": "success",
                        "result": step_output,
                        "error": None,
                        "duration_ms": int((time.time() - step_start) * 1000),
                        "usage": usage,
                        "estimated_cost_usd": cost,
                        "attempts": attempts_log
                        + [{"model": model, "attempt": attempt, "ok": True}],
                    }
                    if self.use_step_cache:
                        self._soft(
                            "step_cache_put",
                            lambda: self.step_cache.put(
                                step.description, rec, model
                            ),
                            result=result,
                        )
                    if verbose:
                        console.print(
                            f"[green]✓ Step {step.step_id} completed[/green]"
                        )
                    if attempt > 1 or model != primary:
                        self._event(
                            "step_recovered",
                            step=step.step_id,
                            model=model,
                            attempt=attempt,
                            primary=primary,
                        )
                    return rec

                except Exception as e:  # noqa: BLE001
                    recovery = classify_error(e)
                    last_recovery = recovery
                    last_error = str(e)
                    last_output = f"Error: {e}"
                    attempts_log.append(
                        {
                            "model": model,
                            "attempt": attempt,
                            "ok": False,
                            "error": last_error[:200],
                            "recovery": recovery,
                        }
                    )
                    self._event(
                        "step_attempt_failed",
                        step=step.step_id,
                        model=model,
                        attempt=attempt,
                        error=last_error[:200],
                        recovery=recovery.get("class"),
                    )
                    logger.warning(
                        "Step %s model=%s attempt=%s failed: %s (%s)",
                        step.step_id,
                        model,
                        attempt,
                        e,
                        recovery.get("class"),
                    )
                    if verbose:
                        console.print(
                            f"[red]✗ Step {step.step_id} attempt {attempt} "
                            f"({model}): {e}[/red]"
                        )
                    retryable = bool(recovery.get("retryable")) and adapt
                    if retryable and attempt < attempts:
                        time.sleep(backoff * attempt)
                        continue
                    # non-retryable or out of retries → next failover model
                    break

            # next model in failover chain
            if adapt and model != models_to_try[-1]:
                self._event(
                    "failover",
                    step=step.step_id,
                    from_model=model,
                    to_model=models_to_try[
                        models_to_try.index(model) + 1
                    ]
                    if model in models_to_try
                    and models_to_try.index(model) + 1 < len(models_to_try)
                    else None,
                )
                continue
            break

        # All attempts failed
        def _blacklist_fail():
            from .model_blacklist import ModelBlacklist

            ModelBlacklist().record_failure(last_model or "unknown")

        self._soft("model_blacklist", _blacklist_fail, result=result)
        return {
            "step": step.step_id,
            "description": step.description,
            "model": last_model,
            "status": "failed",
            "result": last_output,
            "error": last_error,
            "duration_ms": int((time.time() - step_start) * 1000),
            "usage": last_usage,
            "estimated_cost_usd": last_cost,
            "recovery": last_recovery,
            "attempts": attempts_log,
        }

    def _build_step_prompt(
        self,
        step: ExecutionStep,
        task: str,
        run_state: Dict[str, Any],
    ) -> str:
        with self._exec_lock:
            skill_block = run_state.get("skill_prompt_block") or ""
            relevant = dict(run_state.get("relevant_context") or {})
            context = run_state.get("context") or ""

        prompt_parts = [step.description]
        if self.config.get("use_constitution", True):
            try:
                from .constitution import format_for_prompt

                prompt_parts.append(format_for_prompt())
            except Exception as e:  # noqa: BLE001
                logger.debug("constitution inject failed: %s", e)
        if skill_block:
            prompt_parts.append(f"\n{skill_block}")
        if relevant.get("relevant_learnings"):
            learnings_text = "\n".join(
                f"- {l.get('content')}"
                for l in relevant["relevant_learnings"][:3]
                if isinstance(l, dict)
            )
            if learnings_text.strip():
                prompt_parts.append(
                    f"\nRelevant past learnings:\n{learnings_text}"
                )
        if relevant.get("warnings"):
            warnings_text = "\n".join(
                f"- {w.get('content')}"
                for w in relevant["warnings"][:2]
                if isinstance(w, dict)
            )
            if warnings_text.strip():
                prompt_parts.append(
                    f"\nWarnings from past experience:\n{warnings_text}"
                )
        if context:
            prompt_parts.append(f"\nContext from previous steps:\n{context}")
        # Light task framing
        prompt_parts.append(f"\n(Overall task: {task[:500]})")
        return "\n".join(prompt_parts)

    def _maybe_await_replan_approval(
        self,
        task_id: str,
        task: str,
        new_steps: List[ExecutionStep],
        failed_now: List[Dict[str, Any]],
        step_records: List[Dict[str, Any]],
        result: Dict[str, Any],
        verbose: bool,
    ) -> str:
        """
        Returns: auto | approved | rejected | waiting
        """
        require = bool(self.config.get("replan_requires_approval", False))
        # Non-interactive without explicit approval requirement → auto
        non_interactive = bool(
            self.config.get("non_interactive")
            or self.config.use_mock
            and not require
        )
        if not require:
            return "auto"

        # Already decided?
        latest = self.hitl.replan_decision(task_id)
        if latest and latest.get("status") == "answered":
            dec = latest.get("decision") or self.hitl._parse_yes_no(
                str(latest.get("answer") or "")
            )
            if dec == "approved":
                return "approved"
            if dec == "rejected":
                return "rejected"

        if latest and latest.get("status") == "open":
            result["clarifications"] = [latest]
            result["metadata"]["pending_replan"] = [
                {"step_id": s.step_id, "description": s.description}
                for s in new_steps
            ]
            return "waiting"

        # Create approval request
        summary = [
            {
                "step_id": s.step_id,
                "description": s.description,
                "depends_on": list(s.depends_on or []),
                "role": s.role,
                "estimated_complexity": s.estimated_complexity,
                "can_run_parallel": s.can_run_parallel,
                "recommended_model": s.recommended_model,
            }
            for s in new_steps
        ]
        reason = (
            f"Task: {task[:300]}\n"
            f"Failures: "
            + "; ".join(
                f"step {f.get('step')}: {f.get('error')}" for f in failed_now[:5]
            )
        )
        entry = self.hitl.request_replan_approval(
            task_id, summary, reason=reason
        )
        result["clarifications"] = [entry]
        result["metadata"]["pending_replan"] = summary
        self._event(
            "replan_awaiting_approval",
            clar_id=entry.get("id"),
            steps=[s.step_id for s in new_steps],
        )
        # Checkpoint so resume works
        self._soft(
            "checkpoint_replan_wait",
            lambda: self.step_cache.save_run_checkpoint(
                task_id,
                task,
                completed_steps=list(step_records),
                remaining_step_ids=[s.step_id for s in new_steps],
                metadata={
                    "pending_replan": summary,
                    "clar_id": entry.get("id"),
                },
            ),
            result=result,
        )
        if verbose:
            console.print(
                f"[yellow]→ Replan needs approval "
                f"(hitl id={entry.get('id')}): "
                f"superai hitl answer {entry.get('id')} approve[/yellow]"
            )
        # non_interactive + require approval → wait (caller returns waiting_human)
        _ = non_interactive
        return "waiting"

    def _steps_from_hitl_payload(
        self, raw: List[Dict[str, Any]]
    ) -> List[ExecutionStep]:
        out: List[ExecutionStep] = []
        for i, item in enumerate(raw or []):
            if not isinstance(item, dict):
                continue
            try:
                out.append(
                    ExecutionStep(
                        step_id=int(item.get("step_id") or (i + 1)),
                        description=str(
                            item.get("description") or f"recovery step {i + 1}"
                        ),
                        depends_on=[
                            int(d) for d in (item.get("depends_on") or [])
                        ],
                        recommended_model=str(
                            item.get("recommended_model") or "auto"
                        ),
                        estimated_complexity=str(
                            item.get("estimated_complexity") or "Medium"
                        ),
                        can_run_parallel=bool(item.get("can_run_parallel")),
                        role=str(item.get("role") or "worker"),
                    )
                )
            except Exception:  # noqa: BLE001
                continue
        return out

    def _council_critique_step(
        self,
        step: ExecutionStep,
        draft: str,
        task: str,
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Critique a step via multi-CLI reviewer board (preferred) and/or model council.

        Gap fill: cli_delegate_reviewers routes critique to available AI CLIs.
        """
        topic = (
            f"Improve this step for overall task.\n"
            f"Overall: {task[:400]}\n"
            f"Step: {step.description}\n"
            f"Draft:\n{draft[:3000]}\n"
            "Vote on the best improved approach; summary should be the improved text."
        )
        meta: Dict[str, Any] = {}

        # 1) Multi-member reviewer board (API models + CLIs) when enabled
        if bool(self.config.get("cli_delegate_reviewers", False)):
            try:
                from .multi_cli_advisory import multi_cli_board

                pref = self.config.get("cli_review_preferred")
                preferred = None
                if pref:
                    preferred = [
                        p.strip()
                        for p in str(pref).split(",")
                        if p.strip()
                    ]
                # Explicit list can mix gpt-4o and cli:gemini@MODEL; else auto mixed
                board = multi_cli_board(
                    topic,
                    mode="review",
                    members=preferred,
                    max_clis=3,
                    dry_run=bool(self.config.use_mock),
                    approve=True,
                    prefer="mixed",
                )
                meta["cli_board"] = {
                    "members": board.get("members"),
                    "clis": board.get("clis"),
                    "verdict": (board.get("board") or {}).get("verdict"),
                    "tally": (board.get("board") or {}).get("tally"),
                }
                bsum = str((board.get("board") or {}).get("summary") or "").strip()
                if bsum and len(bsum) >= 8:
                    meta["source"] = "multi_cli_review"
                    return bsum, meta
            except Exception as e:  # noqa: BLE001
                meta["cli_board_error"] = str(e)[:200]

        # 2) Fallback: multi-model/CLI council (defaults prefer cli:* members)
        try:
            from .council import Council
            from .multi_cli_advisory import default_council_members

            prefer_clis = bool(self.config.get("council_prefer_clis", True))
            members = default_council_members(
                3, prefer_clis=prefer_clis, registry=self.model_registry
            )
            out = Council(
                caller=self.model_caller, registry=self.model_registry
            ).run(
                topic,
                models=members,
                with_critique=True,
            )
            decision = out.get("decision") or {}
            text = (
                decision.get("summary")
                or decision.get("winner_summary")
                or decision.get("rationale")
            )
            if not text and out.get("proposals"):
                text = (out["proposals"][0] or {}).get("summary")
            meta["voting_mode"] = out.get("voting_mode")
            meta["members"] = out.get("members")
            meta["source"] = "council"
            if text and len(str(text).strip()) >= 8:
                return str(text), meta
            return None, {**meta, "note": "council produced no usable summary"}
        except Exception as e:  # noqa: BLE001
            logger.warning("Council critic failed: %s", e)
            self._degraded.append(
                {"feature": "council_critic", "error": str(e)[:300]}
            )
            return None, {**meta, "error": str(e)[:200]}

    def _run_with_clis(
        self,
        task: str,
        clis: List[str],
        *,
        dry_run: bool = True,
        approve: bool = False,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """Fan-out external CLIs through ParallelCLIManager (shared Memory Palace)."""
        from .cli_pool import ParallelCLIManager

        if verbose:
            console.print(
                f"[cyan]→ Multi-CLI fan-out: {clis} "
                f"(dry_run={dry_run})[/cyan]"
            )
        return ParallelCLIManager().run_agentic_parallel(
            task,
            clis=clis,
            max_workers=max(1, min(4, len(clis))),
            dry_run=dry_run,
            auto_approve=approve or dry_run,
        )

    def _replan_after_failure(
        self,
        task: str,
        task_type: str,
        failed_steps: List[Dict[str, Any]],
        completed_ok: List[Dict[str, Any]],
        plan_steps: List[ExecutionStep],
        verbose: bool,
    ) -> List[ExecutionStep]:
        """Create a recovery plan for remaining work after hard step failures."""
        fail_blob = "; ".join(
            f"step {s.get('step')}: {s.get('error') or s.get('description')}"
            for s in failed_steps[:5]
        )
        ok_blob = "; ".join(
            f"step {s.get('step')} ok"
            for s in completed_ok[:8]
        )
        recovery_task = (
            f"Original task: {task}\n"
            f"Task type: {task_type}\n"
            f"Completed successfully: {ok_blob or 'none'}\n"
            f"Failures to recover from: {fail_blob}\n"
            "Create a short recovery plan that finishes the original goal, "
            "avoiding the failed approaches."
        )
        try:
            use_llm = bool(self.config.get("prefer_llm_planner", True)) and (
                not self.config.use_mock
            )
            new_steps = self.task_planner.create_plan(
                recovery_task, use_llm=use_llm or None
            )
            if not new_steps:
                return []
            # Offset step ids so they don't collide
            max_id = max(
                [s.step_id for s in plan_steps]
                + [int(s.get("step") or 0) for s in completed_ok + failed_steps]
                + [0]
            )
            offset = max_id
            remapped: List[ExecutionStep] = []
            for s in new_steps:
                remapped.append(
                    ExecutionStep(
                        step_id=s.step_id + offset,
                        description=f"[recovery] {s.description}",
                        depends_on=[d + offset for d in (s.depends_on or [])],
                        recommended_model=s.recommended_model,
                        estimated_complexity=s.estimated_complexity,
                        can_run_parallel=s.can_run_parallel,
                        role=s.role,
                    )
                )
            if verbose:
                self.task_planner.print_plan(remapped)
            return remapped
        except Exception as e:  # noqa: BLE001
            logger.warning("Replan failed: %s", e)
            self._degraded.append({"feature": "replan", "error": str(e)[:300]})
            return []

    def _execute_plan_steps(
        self,
        plan_steps: List[ExecutionStep],
        run_one,
        verbose: bool = False,
        already_done: Optional[Set[int]] = None,
    ) -> tuple:
        """
        Topological execution: ready steps with can_run_parallel run concurrently.
        Returns (step_records sorted by step_id, meta).
        """
        by_id: Dict[int, ExecutionStep] = {s.step_id: s for s in plan_steps}
        completed: Set[int] = set(already_done or set())
        # Treat already-done as satisfied deps without re-running
        records_by_id: Dict[int, Dict[str, Any]] = {}
        batches = 0
        parallel_runs = 0

        def deps_met(step: ExecutionStep) -> bool:
            return all(d in completed for d in (step.depends_on or []))

        remaining = set(by_id.keys()) - completed
        deadlocks_fixed = 0

        use_progress = not verbose and len(plan_steps) > 1
        progress_ctx = None
        task_prog = None
        if use_progress:
            progress_ctx = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("{task.completed}/{task.total}"),
                TimeElapsedColumn(),
                console=console,
                transient=True,
            )
            progress_ctx.__enter__()
            task_prog = progress_ctx.add_task(
                "Executing steps", total=max(1, len(remaining))
            )

        try:
            while remaining:
                ready = [
                    by_id[sid]
                    for sid in sorted(remaining)
                    if deps_met(by_id[sid])
                ]
                if not ready:
                    # Deadlock / bad deps — break cycle by dropping unsatisfied deps
                    deadlocks_fixed += 1
                    self._event(
                        "dep_repair",
                        remaining=sorted(remaining),
                        action="run_serial_ignoring_broken_deps",
                    )
                    for sid in list(remaining):
                        step = by_id[sid]
                        # Soft-repair: clear unmet deps so we can progress
                        unmet = [
                            d for d in (step.depends_on or []) if d not in completed
                        ]
                        if unmet:
                            step.depends_on = [
                                d for d in (step.depends_on or []) if d in completed
                            ]
                    ready = [
                        by_id[sid]
                        for sid in sorted(remaining)
                        if deps_met(by_id[sid])
                    ]
                    if not ready:
                        ready = [by_id[sid] for sid in sorted(remaining)]

                parallelizable = [
                    s for s in ready if s.can_run_parallel and len(ready) > 1
                ]
                serial = [s for s in ready if s not in parallelizable]

                batches += 1
                batch: List[ExecutionStep] = []
                if len(parallelizable) >= 2:
                    batch = parallelizable
                elif ready:
                    batch = [ready[0]]
                    serial = ready[1:]

                if len(batch) > 1 and all(s.can_run_parallel for s in batch):
                    if verbose:
                        console.print(
                            f"[dim]→ Parallel batch: steps "
                            f"{[s.step_id for s in batch]}[/dim]"
                        )
                    parallel_runs += len(batch)
                    with ThreadPoolExecutor(max_workers=min(4, len(batch))) as pool:
                        futs = {pool.submit(run_one, s): s for s in batch}
                        for fut in as_completed(futs):
                            step = futs[fut]
                            rec = fut.result()
                            records_by_id[step.step_id] = rec
                            completed.add(step.step_id)
                            remaining.discard(step.step_id)
                            if task_prog is not None and progress_ctx is not None:
                                progress_ctx.update(
                                    task_prog,
                                    description=(
                                        f"Step {step.step_id}: "
                                        f"{step.description[:40]}"
                                    ),
                                )
                                progress_ctx.advance(task_prog)
                else:
                    for step in batch:
                        if task_prog is not None and progress_ctx is not None:
                            progress_ctx.update(
                                task_prog,
                                description=(
                                    f"Step {step.step_id}: "
                                    f"{step.description[:40]}"
                                ),
                            )
                        rec = run_one(step)
                        records_by_id[step.step_id] = rec
                        completed.add(step.step_id)
                        remaining.discard(step.step_id)
                        if task_prog is not None and progress_ctx is not None:
                            progress_ctx.advance(task_prog)

                for step in serial:
                    if step.step_id not in remaining:
                        continue
                    if not deps_met(step):
                        continue
                    if task_prog is not None and progress_ctx is not None:
                        progress_ctx.update(
                            task_prog,
                            description=(
                                f"Step {step.step_id}: {step.description[:40]}"
                            ),
                        )
                    rec = run_one(step)
                    records_by_id[step.step_id] = rec
                    completed.add(step.step_id)
                    remaining.discard(step.step_id)
                    if task_prog is not None and progress_ctx is not None:
                        progress_ctx.advance(task_prog)
        finally:
            if progress_ctx is not None:
                progress_ctx.__exit__(None, None, None)

        ordered = [records_by_id[sid] for sid in sorted(records_by_id.keys())]
        meta = {
            "batches": batches,
            "parallel_step_runs": parallel_runs,
            "total_steps": len(plan_steps),
            "dep_repairs": deadlocks_fixed,
        }
        return ordered, meta

    def _maybe_auto_create_skills(
        self, task_type: str, min_success_count: int = 3
    ) -> List[str]:
        summary = self.learning_engine.get_learnings_summary(task_type=task_type)
        if summary.get("success_count", 0) < min_success_count:
            return []
        return self.learning_engine.create_skills_from_learnings(
            min_success_count=min_success_count
        )

    def _extract_response_text(self, call_result: Any) -> str:
        if isinstance(call_result, dict):
            return str(call_result.get("response", call_result))
        return str(call_result)

    def _synthesize_results(self, original_task: str, results: List[Dict]) -> str:
        """Combine multi-step results into a final answer."""
        synthesis_prompt = f"Original Task: {original_task}\n\nStep Results:\n"
        for r in results:
            synthesis_prompt += (
                f"\n--- Step {r['step']}: {r['description']} ---\n{r['result']}\n"
            )
        synthesis_prompt += (
            "\n\nPlease synthesize the above step results into a single, "
            "coherent, and complete final answer."
        )

        try:
            synth_model = (
                self.config.default_supervisor
                or self.model_router.select_model(original_task)
            )
            call_result = self.model_caller.call(
                model=synth_model,
                prompt=synthesis_prompt,
            )
            return self._extract_response_text(call_result)
        except Exception as e:  # noqa: BLE001
            logger.warning("Synthesis LLM failed, concatenating steps: %s", e)
            self._degraded.append(
                {"feature": "synthesis", "error": str(e)[:300]}
            )
            self._event("synthesis_fallback", error=str(e)[:200])
            parts = [str(r.get("result", "")) for r in results]
            return "\n\n".join(parts)
