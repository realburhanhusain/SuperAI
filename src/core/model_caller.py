"""
ModelCaller - Multi-provider model calling layer (Phase 2)

Mock mode + real APIs. Integrates LoadBalancer for fallback / circuit breaker.
Attaches token usage and estimated cost when available.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional

from .load_balancer import LoadBalancer, ProviderCandidate
from .provider_health import ProviderHealthStore

logger = logging.getLogger(__name__)


from .provider_catalog import (
    NATIVE_PROVIDERS,
    OPENAI_COMPAT_PROVIDERS,
    PROVIDER_HINTS as _MODEL_PROVIDER_HINTS,
    api_key_env_names,
    get_openai_compat_config,
    resolve_compat_provider,
)


class ModelCaller:
    def __init__(
        self,
        use_mock: Optional[bool] = None,
        registry=None,
        load_balancer: Optional[LoadBalancer] = None,
        health_store: Optional[ProviderHealthStore] = None,
    ):
        if use_mock is None:
            self.use_mock = not self._has_any_api_key()
        else:
            self.use_mock = use_mock
        self.registry = registry
        self.load_balancer = load_balancer or LoadBalancer()
        self.health_store = health_store or ProviderHealthStore()
        try:
            self.health_store.apply_to_circuit_breakers(self.load_balancer)
        except Exception:  # noqa: BLE001
            pass

        self.providers = {
            **{k: str(v.get("label") or k) for k, v in OPENAI_COMPAT_PROVIDERS.items()},
            **{k: str(v.get("label") or k) for k, v in NATIVE_PROVIDERS.items()},
        }

    def _has_any_api_key(self) -> bool:
        if any(os.getenv(k) for k in api_key_env_names()):
            return True
        # Local OpenAI-compatible servers often need no key
        return False

    def list_supported_providers(self) -> Dict[str, str]:
        return self.providers

    def call(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        prompt: str = "",
        system_prompt: Optional[str] = None,
        use_fallback: bool = True,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if not model:
            raise ValueError("ModelCaller.call requires a model name")

        # Build failover list of ready models (V3 A M2)
        models_to_try: List[str] = [str(model)]
        if use_fallback and self.registry and not self.use_mock:
            try:
                from .readiness import check_model_ready

                for name in self.registry.list_all_models():
                    if str(name) == str(model):
                        continue
                    if len(models_to_try) >= 4:
                        break
                    if check_model_ready(
                        str(name), use_mock=False, registry=self.registry
                    ).get("ok"):
                        models_to_try.append(str(name))
            except Exception:
                pass

        if not self.use_mock:
            try:
                from .readiness import assert_ready_or_error, check_model_ready

                ready = [
                    m
                    for m in models_to_try
                    if check_model_ready(
                        m, use_mock=False, registry=self.registry
                    ).get("ok")
                ]
                if not ready:
                    blocked = assert_ready_or_error(str(model), use_mock=False)
                    if blocked:
                        blocked["response"] = blocked.get("error")
                        blocked["provider"] = (blocked.get("readiness") or {}).get(
                            "provider"
                        )
                        blocked["failover_attempted"] = models_to_try
                        return blocked
                models_to_try = ready
            except Exception:
                pass

        vision_attachments = kwargs.get("vision_attachments")
        last: Optional[Dict[str, Any]] = None
        primary_model = models_to_try[0]
        for mid in models_to_try:
            last = self._call_one_model(
                provider=provider if mid == primary_model else None,
                model=mid,
                prompt=prompt,
                system_prompt=system_prompt,
                use_fallback=use_fallback,
                vision_attachments=vision_attachments,
            )
            if last and str(last.get("status")) != "error" and not last.get(
                "blocked"
            ):
                if mid != primary_model:
                    last["failover_from"] = primary_model
                    last["model"] = mid
                return last
        return last or {
            "status": "error",
            "response": "all_models_failed",
            "model": model,
            "ok": False,
        }

    def _call_one_model(
        self,
        provider: Optional[str],
        model: str,
        prompt: str,
        system_prompt: Optional[str],
        use_fallback: bool,
        vision_attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        # Dual-registered external CLIs: cli:aider, cli:claude, …
        if str(model).startswith("cli:") or (
            self.registry
            and self.registry.get_model(model)
            and getattr(self.registry.get_model(model), "provider", None)
            == "external_cli"
        ):
            return self._call_external_cli(model, prompt)

        info = self.registry.get_model(model) if self.registry else None
        primary = provider or (info.provider if info else self._resolve_provider(model))

        if not self.health_store.can_call(primary) and not self.use_mock:
            logger.warning(
                "Provider %s throttled/circuit-open; trying anyway via LB", primary
            )

        candidates: List[ProviderCandidate] = [
            ProviderCandidate(
                provider=primary,
                model_name=model,
                cost_per_1k=float(info.cost_per_1k_tokens) if info else 0.0,
                latency_tier=int(info.latency_tier) if info else 2,
            )
        ]

        if use_fallback and self.registry and info:
            for name in self.registry.list_all_models():
                other = self.registry.get_model(name)
                if not other or other.provider == primary:
                    continue
                if other.model_id == info.model_id:
                    candidates.append(
                        ProviderCandidate(
                            provider=other.provider,
                            model_name=model,
                            cost_per_1k=other.cost_per_1k_tokens,
                            latency_tier=other.latency_tier,
                        )
                    )

        def _invoke(prov: str) -> Dict[str, Any]:
            start = time.time()
            try:
                result = self._call_provider(
                    provider=prov,
                    model=model,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    vision_attachments=vision_attachments,
                )
                latency = time.time() - start
                tokens = int((result.get("usage") or {}).get("total_tokens") or 0)
                if result.get("status") == "error":
                    self.health_store.record_failure(
                        prov, error=str(result.get("response")), latency=latency
                    )
                    raise RuntimeError(result.get("response") or "provider error")
                self.health_store.record_success(prov, latency=latency, tokens=tokens)
                return result
            except Exception as e:
                latency = time.time() - start
                self.health_store.record_failure(prov, error=str(e), latency=latency)
                raise

        if self.use_mock:
            try:
                return self.load_balancer.execute_with_fallback(
                    candidates, model, _invoke, max_retries_per_provider=0
                )
            except Exception:  # noqa: BLE001
                return self._mock_call(primary, model, prompt)

        try:
            return self.load_balancer.execute_with_fallback(
                candidates, model, _invoke, max_retries_per_provider=1
            )
        except Exception as e:  # noqa: BLE001
            logger.error(
                "All providers failed for %s: %s — falling back to mock", model, e
            )
            result = self._mock_call(primary, model, prompt)
            result["fallback_reason"] = str(e)
            result["status"] = "error"
            return result

    def stream(
        self,
        model: str,
        prompt: str,
        provider: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ):
        """
        Streaming foundation (F2.5).

        Yields text chunks. Live OpenAI-compatible streaming when available;
        otherwise yields a single chunk from a normal call.
        """
        info = self.registry.get_model(model) if self.registry else None
        prov = provider or (info.provider if info else self._resolve_provider(model))

        if self.use_mock:
            full = self._mock_call(prov, model, prompt)
            text = str(full.get("response") or "")
            # Fake stream in small pieces
            step = max(1, len(text) // 4)
            for i in range(0, len(text), step):
                yield text[i : i + step]
            return

        # Live streaming for OpenAI-compatible providers (catalog + registry base_url)
        prov_l = resolve_compat_provider(prov)
        if get_openai_compat_config(prov_l) or self._registry_openai_endpoint(model):
            try:
                yield from self._stream_openai_compatible(
                    prov_l,
                    model,
                    prompt,
                    system_prompt,
                )
                return
            except Exception as e:  # noqa: BLE001
                logger.warning("Stream failed (%s); falling back to non-stream", e)

        # Fallback: non-streaming single yield
        result = self.call(
            provider=prov, model=model, prompt=prompt, system_prompt=system_prompt
        )
        yield str(result.get("response") or "")

    def _stream_openai_compatible(
        self,
        provider: str,
        model: str,
        prompt: str,
        system_prompt: Optional[str],
    ):
        from openai import OpenAI

        base_url, api_key, _ = self._resolve_openai_endpoint(provider, model)
        client = OpenAI(api_key=api_key, base_url=base_url)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        stream = client.chat.completions.create(
            model=self._model_id(model),
            messages=messages,
            temperature=0.7,
            stream=True,
        )
        start = time.time()
        total_chars = 0
        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                total_chars += len(delta)
                yield delta
        # Approximate token usage from chars
        tokens = max(1, total_chars // 4)
        self.health_store.record_success(
            provider, latency=time.time() - start, tokens=tokens
        )

    def _call_external_cli(self, model: str, prompt: str) -> Dict[str, Any]:
        """
        Invoke dual-registered external CLI as if it were a model.

        SuperAI integration (context inject, Memory Palace write-back, audit)
        lives in ExternalCLITool.run — single path for orchestrator / cli_pool / here.

        Supports inner model selectors: cli:gemini@MODEL, gemini@MODEL.
        """
        from .config import Config
        from .external_cli import ExternalCLIRegistry, ExternalCLITool, split_cli_selector

        base, cli_model = split_cli_selector(str(model))
        # Registry lookup on canonical cli:name (without @model)
        reg_key = f"cli:{base}" if base else str(model)
        info = self.registry.get_model(reg_key) if self.registry else None
        if info is None and self.registry:
            info = self.registry.get_model(model)

        if base:
            cli_name = base
        else:
            cli_name = model.split(":", 1)[-1] if ":" in str(model) else str(model)
            if "@" in cli_name:
                cli_name, right = cli_name.split("@", 1)
                cli_model = cli_model or (right.strip() or None)
        if info and info.model_id and not cli_model:
            # model_id on dual-registered entries is the CLI binary name, not API model
            if info.model_id != cli_name and info.provider != "external_cli":
                cli_name = info.model_id

        label = f"cli:{cli_name}" + (f"@{cli_model}" if cli_model else "")

        # Honor require_human_approval — never hardcode auto_approve for live CLIs
        require_approval = True
        try:
            require_approval = bool(Config().get("require_human_approval", True))
        except Exception:  # noqa: BLE001
            require_approval = True

        dry = bool(self.use_mock)
        try:
            avail = ExternalCLIRegistry().available()
            if cli_name not in avail:
                dry = True
        except Exception:  # noqa: BLE001
            dry = True
        if info and (info.extra or {}).get("available") is False:
            dry = True

        # M9: interactive approval when TTY; blocked (not success) if denied
        approved = not require_approval
        denial_reason: Optional[str] = None
        if require_approval and not dry:
            try:
                from .approval_tui import prompt_approval

                approved = prompt_approval(
                    f"External CLI `{cli_name}`"
                    + (f" model={cli_model}" if cli_model else ""),
                    detail=prompt[:1500],
                    default=False,
                )
            except Exception:
                approved = False
            if not approved:
                denial_reason = (
                    f"External CLI `{cli_name}` blocked: human approval denied "
                    "or unavailable (not counted as success)"
                )
                return {
                    "status": "error",
                    "response": denial_reason,
                    "provider": "external_cli",
                    "model": label,
                    "mock": False,
                    "blocked": True,
                    "usage": {"total_tokens": 0},
                    "estimated_cost_usd": 0.0,
                    "external_cli": {
                        "ok": False,
                        "cli": cli_name,
                        "cli_model": cli_model,
                        "error": denial_reason,
                        "approved": False,
                    },
                    "context_id": None,
                    "memory_write": None,
                    "integrated": True,
                }

        tool = ExternalCLITool(
            auto_approve=approved,
            dry_run=dry,
            with_context=True,
            write_memory=True,
        )
        env = tool.run(
            cli_name,
            prompt,
            approve=approved,
            source="model_caller",
            task_type="coding",
            role="worker",
            cli_model=cli_model,
        )
        text = env.stdout or env.stderr or env.error or ""
        ctx_id = (env.metadata or {}).get("context_id")
        if tool.dry_run and not text:
            text = (
                f"[external_cli:{cli_name}"
                + (f"@{cli_model}" if cli_model else "")
                + f" dry-run] SuperAI-integrated delegation context={ctx_id}."
            )
        # Dry-run only counts as success when intentionally mock/unavailable — not after denial
        ok = bool(env.ok) if not tool.dry_run else True
        if tool.dry_run and not env.ok and env.error and not self.use_mock:
            # forced dry because missing binary: still surface as mock success for demos
            ok = True
        ext = env.to_dict() if hasattr(env, "to_dict") else {}
        if isinstance(ext, dict) and cli_model:
            ext.setdefault("cli_model", cli_model)
        return {
            "status": "success" if ok else "error",
            "response": text or env.error,
            "provider": "external_cli",
            "model": label,
            "cli_model": cli_model,
            "mock": bool(tool.dry_run),
            "usage": {"total_tokens": max(1, len(prompt) // 4)},
            "estimated_cost_usd": 0.0,
            "external_cli": ext,
            "context_id": ctx_id,
            "memory_write": (env.metadata or {}).get("memory_write"),
            "integrated": True,
        }

    def _call_provider(
        self,
        provider: str,
        model: str,
        prompt: str,
        system_prompt: Optional[str],
        vision_attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        if self.use_mock:
            return self._mock_call(provider, model, prompt)

        provider_l = resolve_compat_provider(provider)
        # Any known OpenAI-compat provider OR registry entry with base_url
        if get_openai_compat_config(provider_l) or self._registry_openai_endpoint(model):
            return self._call_openai_compatible(
                provider_l,
                model,
                prompt,
                system_prompt,
                vision_attachments=vision_attachments,
            )
        if provider_l == "anthropic":
            return self._call_anthropic(model, prompt, system_prompt)
        if provider_l == "google":
            return self._call_google(model, prompt, system_prompt)
        if provider_l == "ollama":
            return self._call_ollama(model, prompt, system_prompt)
        # Unknown provider with base_url on model still attempted via openai client
        if self._registry_openai_endpoint(model):
            return self._call_openai_compatible(provider_l, model, prompt, system_prompt)
        return self._mock_call(provider, model, prompt)

    def _resolve_provider(self, model: str) -> str:
        if self.registry is not None:
            info = self.registry.get_model(model)
            if info:
                return info.provider
        lower = model.lower()
        for needle, prov in _MODEL_PROVIDER_HINTS.items():
            if needle in lower:
                return prov
        return "openai"

    def _model_id(self, model: str) -> str:
        if self.registry is not None:
            info = self.registry.get_model(model)
            if info and info.model_id:
                return info.model_id
        return model

    def _estimate_cost(self, model: str, total_tokens: int) -> float:
        if not self.registry or total_tokens <= 0:
            return 0.0
        info = self.registry.get_model(model)
        if not info:
            return 0.0
        return round((total_tokens / 1000.0) * float(info.cost_per_1k_tokens or 0.0), 6)

    def _attach_usage(
        self,
        payload: Dict[str, Any],
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        total = total_tokens if total_tokens is not None else (prompt_tokens + completion_tokens)
        payload["usage"] = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total,
        }
        payload["estimated_cost_usd"] = self._estimate_cost(model, total)
        return payload

    def _registry_openai_endpoint(self, model: str) -> bool:
        """True if registry model has a base_url (treat as OpenAI-compatible)."""
        if not self.registry:
            return False
        info = self.registry.get_model(model)
        return bool(info and info.base_url)

    def _resolve_openai_endpoint(
        self, provider: str, model: str
    ) -> tuple[str, str, Optional[str]]:
        """
        Resolve (base_url, api_key, env_name).

        Priority: ModelInfo.base_url + api_key_env > provider catalog.
        """
        provider = resolve_compat_provider(provider)
        base_url: Optional[str] = None
        env_name: Optional[str] = None
        allow_empty = False
        default_key = "sk-local"

        info = self.registry.get_model(model) if self.registry else None
        if info:
            if info.base_url:
                base_url = str(info.base_url).rstrip("/")
            if info.api_key_env:
                env_name = info.api_key_env

        cat = get_openai_compat_config(provider)
        if cat:
            if not base_url:
                base_url = str(cat.get("base_url") or "").rstrip("/")
            if not env_name:
                env_name = cat.get("env")
            allow_empty = bool(cat.get("allow_empty_key"))
            default_key = str(cat.get("default_key") or default_key)

        if not base_url:
            raise RuntimeError(
                f"No base_url for provider={provider} model={model}. "
                "Register with: superai models-register --name … --base-url …"
            )

        api_key = (os.getenv(env_name) or "").strip() if env_name else ""
        if not api_key:
            if allow_empty or provider in {
                "lmstudio",
                "vllm",
                "ollama_openai",
                "custom",
            }:
                api_key = default_key
            else:
                raise RuntimeError(
                    f"No API key for {provider}"
                    + (f" ({env_name})" if env_name else "")
                    + ". Set the env var or superai secrets set."
                )
        return base_url, api_key, env_name

    def _call_openai_compatible(
        self,
        provider: str,
        model: str,
        prompt: str,
        system_prompt: Optional[str],
        vision_attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("Please install: pip install openai") from None

        base_url, api_key, _ = self._resolve_openai_endpoint(provider, model)
        client = OpenAI(api_key=api_key, base_url=base_url)
        messages: List[Dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        # S2: multimodal vision content when attachments provided
        if vision_attachments:
            try:
                from .multimodal import vision_messages

                messages.extend(vision_messages(prompt, vision_attachments))
            except Exception:
                messages.append({"role": "user", "content": prompt})
        else:
            messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=self._model_id(model),
            messages=messages,
            temperature=0.7,
        )

        usage = getattr(response, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        total_tokens = int(getattr(usage, "total_tokens", 0) or (prompt_tokens + completion_tokens))

        payload = {
            "provider": provider,
            "model": model,
            "base_url": base_url,
            "response": response.choices[0].message.content,
            "status": "success",
            "mock": False,
        }
        return self._attach_usage(payload, model, prompt_tokens, completion_tokens, total_tokens)

    def _call_anthropic(
        self, model: str, prompt: str, system_prompt: Optional[str]
    ) -> Dict[str, Any]:
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("pip install anthropic") from None

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("No ANTHROPIC_API_KEY")

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=self._model_id(model),
            max_tokens=4096,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
        )
        usage = getattr(response, "usage", None)
        prompt_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        payload = {
            "provider": "anthropic",
            "model": model,
            "response": response.content[0].text,
            "status": "success",
            "mock": False,
        }
        return self._attach_usage(payload, model, prompt_tokens, completion_tokens)

    def _call_google(
        self, model: str, prompt: str, system_prompt: Optional[str]
    ) -> Dict[str, Any]:
        try:
            import google.generativeai as genai
        except ImportError:
            raise RuntimeError("pip install google-generativeai") from None

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("No GOOGLE_API_KEY")

        genai.configure(api_key=api_key)
        model_instance = genai.GenerativeModel(self._model_id(model))
        full_prompt = f"{system_prompt}\n{prompt}" if system_prompt else prompt
        response = model_instance.generate_content(full_prompt)

        # Rough token estimate when API does not return usage
        text = response.text or ""
        est_prompt = max(1, len(full_prompt) // 4)
        est_completion = max(1, len(text) // 4)
        payload = {
            "provider": "google",
            "model": model,
            "response": text,
            "status": "success",
            "mock": False,
        }
        return self._attach_usage(payload, model, est_prompt, est_completion)

    def _call_ollama(
        self, model: str, prompt: str, system_prompt: Optional[str]
    ) -> Dict[str, Any]:
        try:
            import requests
        except ImportError:
            raise RuntimeError("pip install requests") from None

        url = "http://localhost:11434/api/generate"
        payload_req = {
            "model": self._model_id(model),
            "prompt": prompt,
            "system": system_prompt or "",
            "stream": False,
        }
        r = requests.post(url, json=payload_req, timeout=180)
        r.raise_for_status()
        data = r.json()
        text = data.get("response", "")
        prompt_tokens = int(data.get("prompt_eval_count") or 0)
        completion_tokens = int(data.get("eval_count") or 0)
        payload = {
            "provider": "ollama",
            "model": model,
            "response": text,
            "status": "success",
            "mock": False,
        }
        return self._attach_usage(payload, model, prompt_tokens, completion_tokens)

    def _mock_call(self, provider: str, model: str, prompt: str) -> Dict[str, Any]:
        logger.info("Using mock response for %s/%s", provider, model)
        snippet = (prompt or "")[:120].replace("\n", " ")
        # Synthetic usage for mock so cost tracking can be exercised
        est_prompt = max(1, len(prompt or "") // 4)
        est_completion = 64
        payload = {
            "provider": provider,
            "model": model,
            "response": (
                f"[Mock Response from {model} via {provider}]\n\n"
                f"Task: {snippet}...\n\n"
                "(Mock mode — set API keys and mock_mode=false for live calls)"
            ),
            "status": "success",
            "mock": True,
        }
        return self._attach_usage(payload, model, est_prompt, est_completion)
