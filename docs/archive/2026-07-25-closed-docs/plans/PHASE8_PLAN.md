# Phase 8 — Nice-to-have product depth

**Inspired by open-source agent patterns (not forks).**  
**Status:** **Implemented** 2026-07-16 — see also `docs/SUPERAI_AGENT.md`  
**Smoke:** Phase 99 still postponed  

| ID | Item | Status | Module / command |
|----|------|--------|------------------|
| N1 | Agent TUI | `[x]` | `agent_tui.py` · `superai agent-tui` |
| N2 | Personal assistant goals | `[x]` | `assistant_goals.py` · `superai goals` |
| N3 | Multimodal images | `[x]` | `multimodal.py` · `ask --image` |
| N4 | Run/subagent graph API | `[x]` | `agent_graph.py` · `agent-graph` · `GET /api/agent-graph` |
| N5 | OpenRouter model refresh | `[x]` | `model_catalog_refresh.py` · `models-refresh-openrouter` |
| N6 | Model bake-off | `[x]` | `model_bakeoff.py` · `superai bakeoff` |
| N7 | Palace tenant | `[x]` | `palace_tenant.py` · config `tenant_id` |
| N8 | Plugin marketplace browse | `[x]` **full** | `plugin_catalog` · bundled catalog JSON · `superai plugin-catalog` · `docs/PLUGIN_MARKETPLACE.md` · `tests/test_plugin_marketplace_n8.py` |

**Progress: 8/8 = 100%** (full multi-agent TUI in `core.superai_agent`)

### N8 detail (V1-N8 production browse)

See **`docs/PLUGIN_MARKETPLACE.md`** for full documentation.

- Offline bundled catalog: `src/core/data/plugin_marketplace_catalog.json`
- Browse: search (`-q`), `--category`, `--tag`, `--sort`, `--limit`
- `--show <id>`, `--categories`, `--status`
- Installed overlay via `PluginRegistry`
- Optional remote catalog URL + sha256 install hooks (M097)


## Usage

```powershell
superai agent-tui --profile balanced --permission ask
superai goals add "weekly review"
superai goals heartbeat
superai goals notify
superai ask "what is in this screenshot" -i path\to\img.png
superai bakeoff "write a hello world" -m gpt-4o,deepseek-chat
superai models-refresh-openrouter --dry-run
superai plugin-catalog -q memory
superai agent-graph
# web: GET /api/agent-graph
```

## Verify

```powershell
pytest tests/test_phase8.py -q
```
