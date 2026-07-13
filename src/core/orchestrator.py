"""
SuperAI Orchestrator (Phase 1 foundation + Phase 2/3 hooks)

Guided by implementation_plan_v2 / detailed plan.
Stabilized wiring: registry → router → caller, structured results, history, logging.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

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
        try:
            self.model_router.refresh_history_stats()
        except Exception:  # noqa: BLE001
            pass
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
        try:
            self.preferences.apply_to_config_defaults(self.config)
        except Exception:  # noqa: BLE001
            pass
        try:
            self.model_registry.register_external_clis_as_models()
        except Exception:  # noqa: BLE001
            pass
        self.step_cache = StepResultCache()
        self.hitl = HITLStore()
        self.use_step_cache = bool(self.config.get("use_step_cache", True))
        logger.info(
            "SuperAIOrchestrator initialized (mock_mode=%s, strategy=%s)",
            self.config.use_mock,
            strategy.value,
        )

    def run_task(
        self,
        task: str,
        forced_model: Optional[str] = None,
        verbose: bool = False,
        resume_task_id: Optional[str] = None,
        pause_on_clarification: bool = True,
    ) -> Dict[str, Any]:
        """Execute a task using planning, routing, and (mock or real) model calls."""
        task = (task or "").strip()
        if not task:
            raise UserInputError(
                "Task description is empty.",
                hint='Provide a task, e.g. superai run "Create a FastAPI hello world"',
            )

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

        # Optional pause when open clarifications exist
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

        # S4 budget pre-check
        try:
            from .budget import BudgetGuard

            bg = BudgetGuard()
            bg.configure(
                daily_usd=float(self.config.get("budget_daily_usd") or 5),
                run_usd=float(self.config.get("budget_run_usd") or 1),
            )
            bg.check_can_spend(estimated_usd=0.01)
        except RuntimeError:
            raise
        except Exception:  # noqa: BLE001
            bg = None  # type: ignore

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
            },
        }

        selected_model: Optional[str] = forced_model
        step_records: List[Dict[str, Any]] = []
        total_tokens = 0
        total_cost = 0.0

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

            # S3: prefer LLM planner when live
            use_llm_plan = bool(self.config.get("prefer_llm_planner", True)) and (
                not self.config.use_mock
            )
            plan_steps = self.task_planner.create_plan(task, use_llm=use_llm_plan or None)
            # Skip already-completed steps on resume
            if resumed_completed:
                done_ids = {
                    int(s.get("step"))
                    for s in resumed_completed
                    if s.get("step") is not None
                }
                plan_steps = [s for s in plan_steps if s.step_id not in done_ids]
                step_records.extend(resumed_completed)
            if verbose:
                self.task_planner.print_plan(plan_steps)

            # Phase 3 hook: mid-task adaptation (best-effort)
            relevant_context: Dict[str, Any] = {}
            try:
                task_type = self.model_router.classify_task(task)
                relevant_context = self.learning_engine.get_relevant_context_for_current_task(
                    task_description=task,
                    task_type=task_type,
                    limit=5,
                )
                if verbose and (
                    relevant_context.get("relevant_learnings")
                    or relevant_context.get("warnings")
                ):
                    console.print("[yellow]→ Using past learnings for this task[/yellow]")
            except Exception as e:  # noqa: BLE001 — best-effort memory
                logger.debug("Could not retrieve past learnings: %s", e)
                if verbose:
                    console.print(f"[yellow]Warning: Could not retrieve past learnings: {e}[/yellow]")

            # Phase 4: relevant skills injected into step prompts
            skill_prompt_block = ""
            skills: List[Dict[str, Any]] = []
            try:
                skills = self.skills_manager.get_relevant_skills(task, top_k=3)
                if skills:
                    skill_prompt_block = self.skills_manager.format_for_prompt(skills)
                    for s in skills:
                        try:
                            self.skills_manager.mark_used(s["name"])
                        except Exception:  # noqa: BLE001
                            pass
                    result["metadata"]["skills_injected"] = True
                    if verbose:
                        console.print(
                            f"[dim]→ Injecting skills: {[s['name'] for s in skills]}[/dim]"
                        )
                result["metadata"]["skills"] = [s.get("name") for s in skills]
            except Exception as e:  # noqa: BLE001
                logger.debug("Skill lookup failed: %s", e)

            context = ""

            def _run_one_step(step):
                nonlocal total_tokens, total_cost, context, selected_model
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

                # Dynamic role switching: supervisor/critic roles prefer configured models
                role = getattr(step, "role", "worker") or "worker"
                if forced_model:
                    selected_model = forced_model
                else:
                    preferred = (
                        self.config.default_supervisor
                        if role in {"supervisor", "critic"}
                        else None
                    ) or self.preferences.preferred_model_for(task_type)
                    if role == "critic" and not preferred:
                        preferred = self.config.default_supervisor
                    selected_model = self.model_router.select_model(
                        task_description=step.description,
                        preferred_model=preferred,
                        verbose=verbose,
                    )

                if verbose:
                    console.print(f"[green]→ Using model: {selected_model}[/green]")

                # Step cache hit
                if self.use_step_cache:
                    cached = self.step_cache.get(step.description, selected_model)
                    if cached and cached.get("status") == "success":
                        if verbose:
                            console.print(
                                f"[dim]→ Cache hit for step {step.step_id}[/dim]"
                            )
                        return {
                            **cached,
                            "step": step.step_id,
                            "description": step.description,
                            "model": selected_model,
                            "cached": True,
                        }

                step_start = time.time()
                step_status = "success"
                step_output: Any = None
                step_error: Optional[str] = None
                usage: Dict[str, Any] = {}
                cost = 0.0

                try:
                    prompt_parts = [step.description]
                    # N14 constitution
                    if self.config.get("use_constitution", True):
                        try:
                            from .constitution import format_for_prompt

                            prompt_parts.append(format_for_prompt())
                        except Exception:  # noqa: BLE001
                            pass
                    if skill_prompt_block:
                        prompt_parts.append(f"\n{skill_prompt_block}")
                    if relevant_context.get("relevant_learnings"):
                        learnings_text = "\n".join(
                            f"- {l['content']}"
                            for l in relevant_context["relevant_learnings"][:3]
                        )
                        prompt_parts.append(f"\nRelevant past learnings:\n{learnings_text}")
                    if relevant_context.get("warnings"):
                        warnings_text = "\n".join(
                            f"- {w['content']}" for w in relevant_context["warnings"][:2]
                        )
                        prompt_parts.append(f"\nWarnings from past experience:\n{warnings_text}")
                    if context:
                        prompt_parts.append(f"\nContext from previous steps:\n{context}")

                    prompt = "\n".join(prompt_parts)
                    call_result = self.model_caller.call(
                        model=selected_model,
                        prompt=prompt,
                    )
                    step_output = self._extract_response_text(call_result)
                    if isinstance(call_result, dict):
                        usage = call_result.get("usage") or {}
                        cost = float(call_result.get("estimated_cost_usd") or 0.0)
                        total_tokens += int(usage.get("total_tokens") or 0)
                        total_cost += cost
                        if call_result.get("status") == "error":
                            step_status = "failed"
                            step_error = str(
                                call_result.get("response") or "provider error"
                            )
                    context += f"\n\n[Step {step.step_id} Result]:\n{str(step_output)[:500]}..."
                    if verbose:
                        if step_status == "success":
                            console.print(f"[green]✓ Step {step.step_id} completed[/green]")
                        else:
                            console.print(
                                f"[red]✗ Step {step.step_id} failed: {step_error}[/red]"
                            )
                except Exception as e:  # noqa: BLE001
                    step_status = "failed"
                    step_error = str(e)
                    step_output = f"Error: {e}"
                    usage = {}
                    cost = 0.0
                    logger.warning("Step %s failed: %s", step.step_id, e)
                    if verbose:
                        console.print(f"[red]✗ Step {step.step_id} failed: {e}[/red]")

                rec = {
                    "step": step.step_id,
                    "description": step.description,
                    "model": selected_model,
                    "status": step_status,
                    "result": step_output,
                    "error": step_error,
                    "duration_ms": int((time.time() - step_start) * 1000),
                    "usage": usage if step_status == "success" else {},
                    "estimated_cost_usd": cost if step_status == "success" else 0.0,
                }
                if self.use_step_cache and step_status == "success":
                    try:
                        self.step_cache.put(step.description, rec, selected_model)
                    except Exception:  # noqa: BLE001
                        pass
                if step_status == "failed":
                    try:
                        from .model_blacklist import ModelBlacklist

                        ModelBlacklist().record_failure(
                            selected_model or "unknown"
                        )
                    except Exception:  # noqa: BLE001
                        pass
                return rec

            # Execute plan respecting depends_on; parallel when can_run_parallel
            _records_lock = threading.Lock()

            def _run_and_checkpoint(step):
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
                # Accumulate for resume checkpoints (thread-safe)
                with _records_lock:
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
                try:
                    self.step_cache.save_run_checkpoint(
                        task_id,
                        task,
                        completed_steps=snapshot,
                        remaining_step_ids=remaining,
                        metadata={"task_type": task_type},
                    )
                except Exception:  # noqa: BLE001
                    pass
                return rec

            _new_records, parallel_meta = self._execute_plan_steps(
                plan_steps,
                _run_and_checkpoint,
                verbose=verbose,
            )
            # step_records already accumulated (resume + new); re-order by step id
            by_id = {
                int(s["step"]): s
                for s in step_records
                if s.get("step") is not None
            }
            step_records = [by_id[k] for k in sorted(by_id.keys())]
            result["metadata"]["execution"] = parallel_meta
            # Clear checkpoint on full success later

            # Synthesize final answer only if we have successful material
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

            any_failed = bool(failed_steps)
            all_failed = bool(step_records) and len(failed_steps) == len(step_records)
            no_steps = not step_records
            overall_success = not all_failed and not no_steps and not any_failed
            # partial: some steps failed but not all
            if all_failed or no_steps:
                overall_status = "failed"
                overall_success = False
            elif any_failed:
                overall_status = "partial"
                overall_success = False  # learning treats partial as not full success
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
                    "estimated_cost_usd": round(total_cost, 6),
                    "metadata": {
                        **result.get("metadata", {}),
                        "task_type": task_type,
                        "steps_succeeded": len(success_steps),
                        "steps_failed": len(failed_steps),
                        "routing_top": self.model_router.explain_selection(task, top_k=3),
                        "load_balancer": self.load_balancer.stats_snapshot(),
                    },
                }
            )

            if verbose:
                color = "green" if overall_success else "yellow"
                console.print(
                    f"\n[bold {color}]Task {overall_status} in {duration:.2f}s "
                    f"({len(success_steps)} ok / {len(failed_steps)} failed)[/bold {color}]"
                )

            # Phase 3: learn from outcome (best-effort) with accurate success signal
            try:
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
            except Exception as e:  # noqa: BLE001
                logger.debug("Could not store learning: %s", e)
                if verbose:
                    console.print(f"[yellow]Warning: Could not store learning: {e}[/yellow]")

            try:
                self.preferences.observe_task(
                    task_type=task_type,
                    model=selected_model or "unknown",
                    success=overall_success,
                    duration=duration,
                )
            except Exception as e:  # noqa: BLE001
                logger.debug("Preference observe failed: %s", e)

            # H6: update contextual bandit from task outcome
            try:
                reward = self.model_router.update_bandit(
                    model=selected_model or "unknown",
                    success=overall_success,
                    latency=duration,
                    cost=total_cost,
                )
                if reward is not None:
                    result["metadata"]["bandit_reward"] = reward
            except Exception as e:  # noqa: BLE001
                logger.debug("Bandit update failed: %s", e)

            # S4 record budget spend
            try:
                from .budget import BudgetGuard

                BudgetGuard().record(usd=total_cost, tokens=total_tokens)
            except Exception:  # noqa: BLE001
                pass

            # S8 audit
            try:
                from .audit_log import AuditLog

                AuditLog().record(
                    "run_task",
                    {
                        "task_id": task_id,
                        "success": overall_success,
                        "model": selected_model,
                        "cost": total_cost,
                    },
                    outcome="ok" if overall_success else "fail",
                )
            except Exception:  # noqa: BLE001
                pass

            # Phase 4: record skill outcomes + auto-create after enough successes
            try:
                for sname in result.get("metadata", {}).get("skills") or []:
                    self.skills_manager.record_outcome(sname, success=overall_success)
            except Exception as e:  # noqa: BLE001
                logger.debug("Skill outcome tracking failed: %s", e)

            if overall_success:
                try:
                    created = self._maybe_auto_create_skills(task_type, min_success_count=3)
                    if created:
                        result["metadata"]["skills_created"] = created
                        # New skills start in sandbox until promoted
                        for cname in created:
                            self.skills_manager.sandbox_skill(cname)
                        if verbose:
                            console.print(
                                f"[green]→ Auto-created skills (sandbox): {created}[/green]"
                            )
                except Exception as e:  # noqa: BLE001
                    logger.debug("Auto skill creation failed: %s", e)
                try:
                    self.step_cache.clear_run(task_id)
                except Exception:  # noqa: BLE001
                    pass
                # Pattern extraction → optional skill suggestions
                try:
                    from .pattern_extract import PatternExtractor

                    patterns = PatternExtractor().extract(min_support=3)
                    if patterns.get("type_patterns"):
                        result["metadata"]["patterns"] = patterns["type_patterns"][:5]
                except Exception:  # noqa: BLE001
                    pass

            logger.info(
                "Task %s finished status=%s duration=%.2fs",
                task_id,
                result["status"],
                duration,
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
            logger.exception("Task %s failed", task_id)
            raise OrchestratorError(str(e)) from e
        finally:
            try:
                self.history.save(result)
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to persist history: %s", e)

        # Typed validation (keeps dict return for history/CLI compatibility)
        try:
            result["_typed"] = TaskResult.from_dict(result).to_dict()
            # Drop internal helper key noise — callers still get plain dict
            typed = result.pop("_typed", None)
            if typed:
                result.setdefault("metadata", {})["task_result_validated"] = True
        except Exception as e:  # noqa: BLE001
            logger.debug("TaskResult validation skipped: %s", e)

        return result

    def _execute_plan_steps(
        self,
        plan_steps: List[ExecutionStep],
        run_one,
        verbose: bool = False,
    ) -> tuple:
        """
        Topological execution: ready steps with can_run_parallel run concurrently.
        Returns (step_records sorted by step_id, meta).
        """
        by_id: Dict[int, ExecutionStep] = {s.step_id: s for s in plan_steps}
        completed: Set[int] = set()
        records_by_id: Dict[int, Dict[str, Any]] = {}
        batches = 0
        parallel_runs = 0

        def deps_met(step: ExecutionStep) -> bool:
            return all(d in completed for d in (step.depends_on or []))

        remaining = set(by_id.keys())

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
            task_prog = progress_ctx.add_task("Executing steps", total=len(plan_steps))

        try:
            while remaining:
                ready = [
                    by_id[sid]
                    for sid in sorted(remaining)
                    if deps_met(by_id[sid])
                ]
                if not ready:
                    # Deadlock / bad deps — run remaining sequentially
                    ready = [by_id[sid] for sid in sorted(remaining)]

                # Split: parallel-eligible vs serial
                parallelizable = [
                    s for s in ready if s.can_run_parallel and len(ready) > 1
                ]
                serial = [s for s in ready if s not in parallelizable]

                batches += 1
                batch: List[ExecutionStep] = []
                if len(parallelizable) >= 2:
                    batch = parallelizable
                    # also run one serial after if any? keep simple: run parallel set first
                elif ready:
                    # single-step batch (serial)
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
                                    description=f"Step {step.step_id}: {step.description[:40]}",
                                )
                                progress_ctx.advance(task_prog)
                else:
                    for step in batch:
                        if verbose:
                            pass  # _run_one_step already prints
                        if task_prog is not None and progress_ctx is not None:
                            progress_ctx.update(
                                task_prog,
                                description=f"Step {step.step_id}: {step.description[:40]}",
                            )
                        rec = run_one(step)
                        records_by_id[step.step_id] = rec
                        completed.add(step.step_id)
                        remaining.discard(step.step_id)
                        if task_prog is not None and progress_ctx is not None:
                            progress_ctx.advance(task_prog)

                # Run leftover serial ready steps that weren't in batch
                for step in serial:
                    if step.step_id not in remaining:
                        continue
                    if not deps_met(step):
                        continue
                    if task_prog is not None and progress_ctx is not None:
                        progress_ctx.update(
                            task_prog,
                            description=f"Step {step.step_id}: {step.description[:40]}",
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
        }
        return ordered, meta

    def _maybe_auto_create_skills(
        self, task_type: str, min_success_count: int = 3
    ) -> List[str]:
        """
        Gate: only auto-create when we have enough successful learnings
        for this task type (avoids skill spam on first run).
        """
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
            # Prefer configured supervisor / a known registry model
            synth_model = (
                self.config.default_supervisor
                or self.model_router.select_model(original_task)
            )
            call_result = self.model_caller.call(
                model=synth_model,
                prompt=synthesis_prompt,
            )
            return self._extract_response_text(call_result)
        except Exception:  # noqa: BLE001
            parts = [str(r.get("result", "")) for r in results]
            return "\n\n".join(parts)
