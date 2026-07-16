"""
SuperAI agent runtime: tool loop + multi-agent + model-agnostic calls.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ..progress_events import get_progress_bus
from ..result_contract import apply_contract
from ..tool_protocol import extract_tool_calls
from .agents import get_agent
from .session import SuperAISessionStore, SessionState
from .tools_bridge import catalog, dispatch_tool


ApproveFn = Callable[[str, Dict[str, Any]], bool]
TokenFn = Callable[[str], None]


@dataclass
class RunResult:
    ok: bool
    response: str
    session_id: str
    agent: str
    model: Optional[str]
    tool_rounds: int = 0
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    tokens: int = 0
    estimated_cost_usd: float = 0.0
    mock: bool = False
    parts: List[Dict[str, Any]] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "ok": self.ok,
            "status": "success" if self.ok else "error",
            "response": self.response,
            "session_id": self.session_id,
            "agent": self.agent,
            "model": self.model,
            "tool_rounds": self.tool_rounds,
            "tool_results": self.tool_results,
            "tokens": self.tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "mock": self.mock,
            "parts": self.parts,
            "members": [self.model] if self.model else [],
            "model_chain": [self.model] if self.model else [],
            "memory_ids": [],
            "dry_run": False,
        }
        return apply_contract(d, mock=self.mock, ok=self.ok)


class AgentRuntime:
    def __init__(
        self,
        store: Optional[SuperAISessionStore] = None,
        *,
        use_mock: Optional[bool] = None,
    ):
        self.store = store or SuperAISessionStore()
        if use_mock is None:
            try:
                from ..config import Config

                self.use_mock = bool(Config().use_mock)
            except Exception:
                self.use_mock = True
        else:
            self.use_mock = use_mock

    def new_session(
        self,
        *,
        agent: str = "build",
        model: Optional[str] = None,
        permission: str = "ask",
        title: str = "",
    ) -> SessionState:
        return self.store.create(
            agent=agent, model=model, permission=permission, title=title
        )

    def run(
        self,
        user_text: str,
        *,
        session: Optional[SessionState] = None,
        session_id: Optional[str] = None,
        agent: Optional[str] = None,
        model: Optional[str] = None,
        permission: Optional[str] = None,
        approve: Optional[ApproveFn] = None,
        on_token: Optional[TokenFn] = None,
        max_rounds: Optional[int] = None,
        max_seconds: Optional[float] = None,
        change_set: Any = None,
        stage_writes: bool = False,
    ) -> RunResult:
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed

        from ..run_trail import append_event, new_run_id
        from ..result_contract import apply_contract

        t0 = time.time()
        run_id = new_run_id()
        bus = get_progress_bus()
        if session is None:
            if session_id:
                session = self.store.load(session_id)
            else:
                session = self.new_session(
                    agent=agent or "build",
                    model=model,
                    permission=permission or "ask",
                )
        if agent:
            session.agent = agent
        if model:
            session.model = model
        if permission:
            session.permission = permission

        role = get_agent(session.agent)
        rounds = max_rounds if max_rounds is not None else role.max_tool_rounds
        mid = session.model or self._default_model()

        # V4 M1 budget pre-check
        try:
            from ..budget import BudgetGuard
            from ..config import Config

            cfg = Config()
            enforce = bool(cfg.get("enforce_budget", True))
            est = 0.02 if self.use_mock else 0.15
            blocked = BudgetGuard().enforce_or_block(est, tokens=500, enforce=enforce)
            if blocked.get("blocked"):
                blocked["session_id"] = session.id
                blocked["run_id"] = run_id
                append_event(run_id, "budget_block", ok=False, detail=blocked.get("error"))
                return RunResult(
                    ok=False,
                    response=str(blocked.get("error") or "budget_blocked"),
                    session_id=session.id,
                    agent=role.id,
                    model=mid,
                    mock=self.use_mock,
                    raw=blocked,
                )
        except Exception:
            pass

        # V4 M3 fail-closed readiness for live
        if not self.use_mock:
            try:
                from ..readiness import check_model_ready

                ready = check_model_ready(mid, use_mock=False)
                if not ready.get("ok"):
                    msg = f"model_not_ready:{mid}:{ready.get('error') or ready}"
                    append_event(run_id, "readiness_block", ok=False, detail=msg)
                    return RunResult(
                        ok=False,
                        response=msg,
                        session_id=session.id,
                        agent=role.id,
                        model=mid,
                        mock=False,
                        raw={"readiness": ready, "run_id": run_id},
                    )
            except Exception:
                pass

        # V4 M6 cheap-first model pick for non-code
        try:
            from ..task_complexity import classify_task, cheap_first_models

            cx = classify_task(user_text)
            if cx.get("prefer_cheap") and not session.model:
                pool = cheap_first_models(
                    [mid, "deepseek-chat", "llama3.2", "gpt-4o-mini", "gpt-4o"],
                    prefer_cheap=True,
                    max_n=1,
                )
                if pool:
                    mid = pool[0]
        except Exception:
            cx = {}

        append_event(
            run_id,
            "start",
            session_id=session.id,
            agent=role.id,
            model=mid,
            detail=user_text[:120],
        )
        self.store.append_message(session, "user", user_text)
        bus.emit("oc_user", text=user_text[:200], agent=session.agent)

        history = self._history_text(session)
        tools_hint = (
            "Workspace tools: "
            + ", ".join(t["name"] for t in catalog())
            + f"\nAgent={role.id} permission={session.permission}"
        )
        # V4 S7 context pack
        try:
            from ..context_pack import pack_context

            packed = pack_context(
                system=role.system_prompt,
                history=history,
                tools_hint=tools_hint,
                user=user_text,
                max_tokens=int(
                    __import__("os").environ.get("SUPERAI_CONTEXT_TOKENS", "6000")
                ),
            )
            system = role.system_prompt
            prompt = packed.get("text") or (
                f"{history}\n\nUser: {user_text}\n\n"
                "If tools are needed, emit tool_call JSON first; otherwise answer."
            )
            if tools_hint not in prompt:
                prompt = f"{tools_hint}\n\n{prompt}"
        except Exception:
            system = role.system_prompt + "\n" + tools_hint
            prompt = (
                f"{history}\n\nUser: {user_text}\n\n"
                "If tools are needed, emit tool_call JSON first; otherwise answer."
            )

        all_tool_results: List[Dict[str, Any]] = []
        parts: List[Dict[str, Any]] = []
        total_tokens = 0
        total_cost = 0.0
        mock = self.use_mock
        final_text = ""
        tool_rounds = 0
        status = "success"
        deadline = t0 + float(max_seconds) if max_seconds else None

        for round_i in range(max(1, rounds)):
            if deadline and time.time() > deadline:
                status = "partial"
                final_text = final_text or "timeout: partial result"
                break
            bus.emit("oc_round", n=round_i + 1, model=mid)

            # V4 M4 stream path when on_token provided
            if on_token:
                text_parts: List[str] = []
                try:
                    from ..model_caller import ModelCaller
                    from ..model_registry import ModelRegistry

                    caller = ModelCaller(
                        use_mock=self.use_mock, registry=ModelRegistry()
                    )
                    for ch in caller.call_stream(
                        model=mid, prompt=prompt, system_prompt=system
                    ):
                        text_parts.append(ch)
                        on_token(ch)
                    text = "".join(text_parts)
                    call = {
                        "response": text,
                        "mock": self.use_mock,
                        "tokens": max(1, len(text) // 4),
                        "estimated_cost_usd": 0.0 if self.use_mock else 0.01,
                    }
                except Exception:
                    call = self._call_model(mid, prompt, system)
                    text = str(call.get("response") or call.get("error") or "")
                    try:
                        from ..token_stream import stream_tokens

                        for ch in stream_tokens(text, emit_progress=False):
                            on_token(ch)
                    except Exception:
                        on_token(text)
            else:
                call = self._call_model(mid, prompt, system)
                text = str(call.get("response") or call.get("error") or "")

            mock = mock or bool(call.get("mock"))
            total_tokens += int(
                (call.get("usage") or {}).get("total_tokens")
                or call.get("tokens")
                or 0
            )
            total_cost += float(call.get("estimated_cost_usd") or 0)

            calls = extract_tool_calls(text)
            if not calls:
                final_text = text
                parts.append({"type": "text", "text": text})
                break

            tool_rounds += 1
            visible = text
            round_results: List[Dict[str, Any]] = []
            perm = session.permission

            def _one(tc: Dict[str, Any]) -> Dict[str, Any]:
                name = str(tc.get("name") or "")
                args = tc.get("arguments") or tc.get("args") or {}
                if not isinstance(args, dict):
                    args = {}
                if role.id in {"plan", "ask"} and name in {
                    "write",
                    "diff_apply",
                    "bash",
                }:
                    res = {
                        "ok": False,
                        "error": "blocked_for_agent",
                        "agent": role.id,
                        "tool": name,
                    }
                elif (
                    stage_writes
                    and change_set is not None
                    and name == "write"
                    and perm != "yolo"
                ):
                    # V4 S10 stage instead of write
                    change_set.stage_write(
                        str(args.get("path") or ""),
                        str(args.get("content") or ""),
                    )
                    res = {
                        "ok": True,
                        "staged": True,
                        "path": args.get("path"),
                        "change_set": change_set.summary(),
                    }
                else:
                    bus.emit("oc_tool", name=name)
                    res = dispatch_tool(
                        name,
                        args,
                        agent_id=role.id,
                        permission_mode=perm,
                        approve_callback=approve,
                    )
                return {"tool_call": tc, "result": res, "name": name, "args": args}

            # V4 S8 parallel independent read tools
            readonly = all(
                str(tc.get("name") or "").lower() in {"read", "grep", "glob"}
                for tc in calls
            )
            if readonly and len(calls) > 1:
                with ThreadPoolExecutor(max_workers=min(4, len(calls))) as ex:
                    futs = [ex.submit(_one, tc) for tc in calls[:8]]
                    for fut in as_completed(futs):
                        item = fut.result()
                        round_results.append(item)
            else:
                for tc in calls[:8]:
                    round_results.append(_one(tc))

            for item in round_results:
                name = item.get("name") or ""
                args = item.get("args") or {}
                res = item.get("result") or {}
                parts.append(
                    {"type": "tool_call", "name": name, "arguments": args}
                )
                parts.append(
                    {
                        "type": "tool_result",
                        "name": name,
                        "ok": res.get("ok"),
                        "result": res,
                    }
                )
                all_tool_results.append(
                    {"tool_call": item.get("tool_call"), "result": res}
                )
                append_event(
                    run_id,
                    "tool",
                    ok=bool(res.get("ok")),
                    detail=f"{name}:{str(res.get('path') or res.get('error') or '')[:80]}",
                    dry_run=bool(res.get("dry_run")),
                )
                try:
                    from ..side_effect_audit import record_side_effect

                    record_side_effect(
                        "superai_agent_tool",
                        name=str(name),
                        ok=bool(res.get("ok")),
                        dry_run=bool(res.get("dry_run")),
                        detail=str(res.get("path") or res.get("error") or "")[:200],
                    )
                except Exception:
                    pass

            prompt = (
                f"{history}\n\nUser: {user_text}\n\n"
                f"Assistant draft:\n{visible[:3000]}\n\n"
                f"Tool results:\n{json.dumps(round_results, default=str)[:6000]}\n\n"
                "Continue. If done, give final answer without more tool_call JSON."
            )
            final_text = visible
        else:
            call = self._call_model(
                mid,
                prompt + "\nFinal answer only, no tools.",
                system,
            )
            final_text = str(call.get("response") or final_text)
            total_tokens += int(
                (call.get("usage") or {}).get("total_tokens") or call.get("tokens") or 0
            )
            total_cost += float(call.get("estimated_cost_usd") or 0)
            parts.append({"type": "text", "text": final_text})

        # record budget spend
        try:
            from ..budget import BudgetGuard

            BudgetGuard().record(usd=total_cost, tokens=total_tokens)
        except Exception:
            pass

        # V4 S3 bandit feedback
        try:
            from ..model_registry import ModelRegistry
            from ..model_router import ModelRouter

            latency = time.time() - t0
            router = ModelRouter(ModelRegistry())
            if hasattr(router, "update_bandit"):
                router.update_bandit(
                    mid,
                    success=status == "success",
                    latency=latency,
                    cost=total_cost,
                )
        except Exception:
            pass

        session.tokens += total_tokens
        session.estimated_cost_usd = round(
            float(session.estimated_cost_usd) + total_cost, 6
        )
        session.model = mid
        self.store.append_message(
            session,
            "assistant",
            final_text,
            parts=parts,
            meta={
                "tool_rounds": tool_rounds,
                "tokens": total_tokens,
                "estimated_cost_usd": total_cost,
                "agent": role.id,
                "model": mid,
                "run_id": run_id,
                "status": status,
            },
        )
        self.store.save(session)
        append_event(
            run_id,
            "done",
            ok=status == "success",
            detail=f"tools={tool_rounds} cost={total_cost}",
            session_id=session.id,
        )
        bus.emit(
            "oc_done",
            ok=status == "success",
            tools=tool_rounds,
            cost=total_cost,
            session=session.id,
            run_id=run_id,
        )

        raw = {
            "session": session.to_dict(),
            "run_id": run_id,
            "status": status,
            "complexity": cx if isinstance(cx, dict) else {},
        }
        if change_set is not None:
            raw["change_set"] = change_set.summary()

        result = RunResult(
            ok=status in {"success", "partial"},
            response=final_text,
            session_id=session.id,
            agent=role.id,
            model=mid,
            tool_rounds=tool_rounds,
            tool_results=all_tool_results,
            tokens=total_tokens,
            estimated_cost_usd=round(total_cost, 6),
            mock=mock,
            parts=parts,
            raw=raw,
        )
        # V4 M2 ensure contract on public result
        d = result.to_dict()
        d["status"] = status if status != "success" else d.get("status")
        d["run_id"] = run_id
        apply_contract(d, mock=mock, ok=result.ok)
        result.raw["contracted"] = d
        return result

    def _history_text(self, session: SessionState, max_msgs: int = 12) -> str:
        msgs = (session.messages or [])[-max_msgs:]
        if not msgs:
            return ""
        lines = ["[Session history]"]
        for m in msgs:
            lines.append(f"{m.get('role')}: {str(m.get('content') or '')[:800]}")
        return "\n".join(lines)

    def _default_model(self) -> str:
        try:
            from ..config import Config

            cfg = Config()
            return str(
                cfg.get("preferred_model")
                or cfg.get("default_model")
                or "gpt-4o"
            )
        except Exception:
            return "gpt-4o"

    def _call_model(
        self, model: str, prompt: str, system: str
    ) -> Dict[str, Any]:
        from ..model_caller import ModelCaller
        from ..model_registry import ModelRegistry

        caller = ModelCaller(use_mock=self.use_mock, registry=ModelRegistry())
        try:
            return caller.call(
                model=model,
                prompt=prompt,
                system_prompt=system,
                use_fallback=True,
            )
        except Exception as e:
            return {
                "status": "error",
                "response": str(e)[:500],
                "mock": self.use_mock,
                "ok": False,
            }
