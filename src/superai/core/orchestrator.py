"""
SuperAI Orchestrator (Phase 1 foundation + Phase 2/3 hooks)

Guided by implementation_plan_v2 / detailed plan.
Stabilized wiring: registry → router → caller, structured results, history, logging.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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
from .provider_health import ProviderHealthStore
from .skills import SkillsManager
from .task_planner import TaskPlanner

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
        self.task_planner = TaskPlanner(self.model_router)
        self.memory_palace = MemoryPalace()
        self.learning_engine = LearningEngine(self.memory_palace)
        self.skills_manager = SkillsManager()
        self.history = TaskHistory()
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
    ) -> Dict[str, Any]:
        """Execute a task using planning, routing, and (mock or real) model calls."""
        task = (task or "").strip()
        if not task:
            raise UserInputError(
                "Task description is empty.",
                hint='Provide a task, e.g. superai run "Create a FastAPI hello world"',
            )

        task_id = self.history.new_task_id()
        started_at = datetime.now(timezone.utc).isoformat()
        start_time = time.time()

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

            plan_steps = self.task_planner.create_plan(task)
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

                if forced_model:
                    selected_model = forced_model
                else:
                    selected_model = self.model_router.select_model(
                        task_description=step.description,
                        preferred_model=self.config.default_supervisor,
                        verbose=verbose,
                    )

                if verbose:
                    console.print(f"[green]→ Using model: {selected_model}[/green]")

                step_start = time.time()
                step_status = "success"
                step_output: Any = None
                step_error: Optional[str] = None
                usage: Dict[str, Any] = {}
                cost = 0.0

                try:
                    prompt_parts = [step.description]
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

                return {
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

            # G1: progress UI for multi-step runs (skip heavy bar in verbose mode)
            if not verbose and len(plan_steps) > 1:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("{task.completed}/{task.total}"),
                    TimeElapsedColumn(),
                    console=console,
                    transient=True,
                ) as progress:
                    task_prog = progress.add_task("Executing steps", total=len(plan_steps))
                    for step in plan_steps:
                        progress.update(
                            task_prog,
                            description=f"Step {step.step_id}: {step.description[:40]}",
                        )
                        step_records.append(_run_one_step(step))
                        progress.advance(task_prog)
            else:
                for step in plan_steps:
                    step_records.append(_run_one_step(step))

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

        return result

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
