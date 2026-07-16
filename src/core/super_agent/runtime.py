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
from .session import AgentSessionStore, SessionState
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
        store: Optional[AgentSessionStore] = None,
        *,
        use_mock: Optional[bool] = None,
    ):
        self.store = store or AgentSessionStore()
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
    ) -> RunResult:
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

        self.store.append_message(session, "user", user_text)
        bus.emit("oc_user", text=user_text[:200], agent=session.agent)

        # Build conversation context
        history = self._history_text(session)
        system = role.system_prompt + (
            f"\nWorkspace tools available: "
            + ", ".join(t["name"] for t in catalog())
            + f"\nAgent={role.id} permission={session.permission}"
        )

        mid = session.model or self._default_model()
        all_tool_results: List[Dict[str, Any]] = []
        parts: List[Dict[str, Any]] = []
        total_tokens = 0
        total_cost = 0.0
        mock = self.use_mock
        final_text = ""
        tool_rounds = 0

        prompt = (
            f"{history}\n\nUser: {user_text}\n\n"
            "If tools are needed, emit tool_call JSON first; otherwise answer."
        )

        for round_i in range(max(1, rounds)):
            bus.emit("oc_round", n=round_i + 1, model=mid)
            call = self._call_model(mid, prompt, system)
            mock = mock or bool(call.get("mock"))
            total_tokens += int(
                (call.get("usage") or {}).get("total_tokens")
                or call.get("tokens")
                or 0
            )
            total_cost += float(call.get("estimated_cost_usd") or 0)
            text = str(call.get("response") or call.get("error") or "")
            if on_token:
                try:
                    from ..token_stream import stream_tokens

                    for ch in stream_tokens(text, emit_progress=False):
                        on_token(ch)
                except Exception:
                    on_token(text)

            calls = extract_tool_calls(text)
            if not calls:
                final_text = text
                parts.append({"type": "text", "text": text})
                break

            tool_rounds += 1
            # strip tool JSON from visible reply partially
            visible = text
            round_results = []
            for tc in calls:
                name = str(tc.get("name") or "")
                args = tc.get("arguments") or tc.get("args") or {}
                if not isinstance(args, dict):
                    args = {}
                # plan/ask force dry for write
                perm = session.permission
                if role.id in {"plan", "ask"} and name in {"write", "diff_apply", "bash"}:
                    res = {
                        "ok": False,
                        "error": "blocked_for_agent",
                        "agent": role.id,
                        "tool": name,
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
                parts.append(
                    {
                        "type": "tool_call",
                        "name": name,
                        "arguments": args,
                    }
                )
                parts.append(
                    {
                        "type": "tool_result",
                        "name": name,
                        "ok": res.get("ok"),
                        "result": res,
                    }
                )
                item = {"tool_call": tc, "result": res}
                round_results.append(item)
                all_tool_results.append(item)
                try:
                    from ..side_effect_audit import record_side_effect

                    record_side_effect(
                        "super_agent_tool",
                        name=name,
                        ok=bool(res.get("ok")),
                        dry_run=bool(res.get("dry_run")),
                        detail=str(res.get("path") or res.get("error") or "")[:200],
                    )
                except Exception:
                    pass

            # follow-up with tool results
            prompt = (
                f"{history}\n\nUser: {user_text}\n\n"
                f"Assistant draft:\n{visible[:3000]}\n\n"
                f"Tool results:\n{json.dumps(round_results, default=str)[:6000]}\n\n"
                "Continue. If done, give final answer without more tool_call JSON."
            )
            final_text = visible  # may be overwritten next round
        else:
            # last round ended with tools — one more call without tools pressure
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
            },
        )
        self.store.save(session)
        bus.emit(
            "oc_done",
            ok=True,
            tools=tool_rounds,
            cost=total_cost,
            session=session.id,
        )

        return RunResult(
            ok=True,
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
            raw={"session": session.to_dict()},
        )

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
