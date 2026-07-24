# Routing pipeline: preferences + bandit (M068 / M050)

**Updated:** 2026-07-24

## Order of application (product contract)

```text
1. Build candidate list (failover / escalate / rank_models top-K)
2. preferences.bias_candidates()   ← M068 sticky preferred + cheap_mode
3. bandit.select() / blend         ← M050 epsilon-greedy (or score blend)
4. call first ready model; on outcome → bandit.update + prefer.observe_task
```

Shared helper: `core.bandit_router.route_candidates(candidates)`.

Wired into:

- `ModelCaller.call` — reorders `models_to_try` (prefs then bandit)
- `ModelRouter.get_best_model` — bias top-K names then bandit explore/exploit
- `call_lifecycle.post_call` — automatic `bandit.update` + preference signals

## Persistence

| Store | Path |
|-------|------|
| Preferences | `~/.superai/preferences.json` |
| Bandit arms | `~/.superai/bandit_state.json` |

## Operator CLI

```powershell
superai pref show
superai pref sticky claude-4-sonnet
superai pref cheap on
superai pref clear

superai bandit status
superai bandit reset
superai --json bandit status
```

Bakeoff pin: `model_bakeoff` can set `preferred_model` on config / prefs — that sticky
then wins step 2 on subsequent routes.

## Honesty

- Bandit needs outcomes; empty arms → neutral until live/mock calls update.
- `SUPERAI_USE_BANDIT=0` disables bandit stage; prefs still apply.
- Cost for rewards comes from call cost attachment (coordinate with AGY spend accuracy).

## Verify

```powershell
pytest tests/test_routing_prefs_bandit_g2.py tests/test_msg_vega_plugin_bandit.py -q
```
