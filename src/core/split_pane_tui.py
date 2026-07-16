"""
N209 — Split-pane TUI layout engine.

Production features (beyond a single fixed layout):
- Named layout presets: classic, h-split, v-split, triple, quad, focus, agent
- Configurable pane ratios (horizontal / vertical)
- Focus cycle + focus-by-name (highlighted border)
- Hide / show individual panes with reflow
- Persist preferences under ~/.superai/tui/split_pane.json
- Pure render API for tests (no interactive terminal required)
- Slash-command handler for agent TUI integration

Does not require Textual; uses Rich Layout (already a SuperAI dependency).
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from rich.console import Group, RenderableType
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


# ---------------------------------------------------------------------------
# Pane catalog
# ---------------------------------------------------------------------------

PANE_IDS: Tuple[str, ...] = (
    "header",
    "messages",
    "tools",
    "events",
    "cost",
    "sessions",
    "changeset",
    "help",
    "status",
)

PANE_TITLES: Dict[str, str] = {
    "header": "header",
    "messages": "messages",
    "tools": "tools",
    "events": "events",
    "cost": "cost / tokens",
    "sessions": "sessions",
    "changeset": "changeset",
    "help": "help",
    "status": "status",
}


# ---------------------------------------------------------------------------
# Layout presets
# ---------------------------------------------------------------------------
# Each preset describes a tree of splits. Nodes:
#   {"kind": "leaf", "pane": "messages"}
#   {"kind": "row"|"col", "ratio": [3,1], "children": [...]}
# Optional size on leaves is applied via Layout(size=N) when positive.

PRESETS: Dict[str, Dict[str, Any]] = {
    "classic": {
        "description": "Messages | tools (2-column)",
        "tree": {
            "kind": "row",
            "ratio": [3, 1],
            "children": [
                {"kind": "leaf", "pane": "messages"},
                {"kind": "leaf", "pane": "tools"},
            ],
        },
    },
    "h-split": {
        "description": "Messages above tools (horizontal stack)",
        "tree": {
            "kind": "col",
            "ratio": [3, 1],
            "children": [
                {"kind": "leaf", "pane": "messages"},
                {"kind": "leaf", "pane": "tools"},
            ],
        },
    },
    "v-split": {
        "description": "Alias of classic vertical split (side-by-side)",
        "tree": {
            "kind": "row",
            "ratio": [1, 1],
            "children": [
                {"kind": "leaf", "pane": "messages"},
                {"kind": "leaf", "pane": "tools"},
            ],
        },
    },
    "triple": {
        "description": "Messages | tools | events",
        "tree": {
            "kind": "row",
            "ratio": [3, 1, 1],
            "children": [
                {"kind": "leaf", "pane": "messages"},
                {"kind": "leaf", "pane": "tools"},
                {"kind": "leaf", "pane": "events"},
            ],
        },
    },
    "quad": {
        "description": "2x2: messages/tools × events/cost",
        "tree": {
            "kind": "col",
            "ratio": [1, 1],
            "children": [
                {
                    "kind": "row",
                    "ratio": [2, 1],
                    "children": [
                        {"kind": "leaf", "pane": "messages"},
                        {"kind": "leaf", "pane": "tools"},
                    ],
                },
                {
                    "kind": "row",
                    "ratio": [1, 1],
                    "children": [
                        {"kind": "leaf", "pane": "events"},
                        {"kind": "leaf", "pane": "cost"},
                    ],
                },
            ],
        },
    },
    "focus": {
        "description": "Single focused pane (fullscreen content)",
        "tree": {"kind": "leaf", "pane": "messages"},
    },
    "agent": {
        "description": "Header + (messages|sidebar) + status footer",
        "tree": {
            "kind": "col",
            "ratio": [0, 1, 0],
            "sizes": [3, None, 3],
            "children": [
                {"kind": "leaf", "pane": "header", "size": 3},
                {
                    "kind": "row",
                    "ratio": [3, 1],
                    "children": [
                        {"kind": "leaf", "pane": "messages"},
                        {
                            "kind": "col",
                            "ratio": [1, 1],
                            "children": [
                                {"kind": "leaf", "pane": "tools"},
                                {"kind": "leaf", "pane": "events"},
                            ],
                        },
                    ],
                },
                {"kind": "leaf", "pane": "status", "size": 3},
            ],
        },
    },
    "ide": {
        "description": "IDE-like: messages + tools/changeset + status",
        "tree": {
            "kind": "col",
            "ratio": [0, 1, 0],
            "sizes": [3, None, 3],
            "children": [
                {"kind": "leaf", "pane": "header", "size": 3},
                {
                    "kind": "row",
                    "ratio": [3, 1],
                    "children": [
                        {"kind": "leaf", "pane": "messages"},
                        {
                            "kind": "col",
                            "ratio": [1, 1, 1],
                            "children": [
                                {"kind": "leaf", "pane": "tools"},
                                {"kind": "leaf", "pane": "changeset"},
                                {"kind": "leaf", "pane": "cost"},
                            ],
                        },
                    ],
                },
                {"kind": "leaf", "pane": "status", "size": 3},
            ],
        },
    },
}

DEFAULT_LAYOUT = "agent"


# ---------------------------------------------------------------------------
# Config state
# ---------------------------------------------------------------------------


@dataclass
class SplitPaneConfig:
    layout: str = DEFAULT_LAYOUT
    focus: str = "messages"
    hidden: List[str] = field(default_factory=list)
    # Optional overrides: "messages:tools" -> [3, 1]
    ratio_overrides: Dict[str, List[float]] = field(default_factory=dict)
    border_focused: str = "bright_cyan"
    border_normal: str = "white"
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "SplitPaneConfig":
        if not data or not isinstance(data, dict):
            return cls()
        hidden = data.get("hidden") or []
        if not isinstance(hidden, list):
            hidden = []
        ro = data.get("ratio_overrides") or {}
        if not isinstance(ro, dict):
            ro = {}
        layout = str(data.get("layout") or DEFAULT_LAYOUT)
        if layout not in PRESETS:
            layout = DEFAULT_LAYOUT
        focus = str(data.get("focus") or "messages")
        if focus not in PANE_IDS:
            focus = "messages"
        return cls(
            layout=layout,
            focus=focus,
            hidden=[str(h) for h in hidden if str(h) in PANE_IDS],
            ratio_overrides={
                str(k): [float(x) for x in (v or [])]
                for k, v in ro.items()
                if isinstance(v, (list, tuple))
            },
            border_focused=str(data.get("border_focused") or "bright_cyan"),
            border_normal=str(data.get("border_normal") or "white"),
            updated_at=data.get("updated_at"),
        )


def config_path() -> Path:
    p = Path.home() / ".superai" / "tui" / "split_pane.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def load_config() -> SplitPaneConfig:
    path = config_path()
    if path.is_file():
        try:
            return SplitPaneConfig.from_dict(
                json.loads(path.read_text(encoding="utf-8"))
            )
        except Exception:
            pass
    return SplitPaneConfig()


def save_config(cfg: SplitPaneConfig) -> Path:
    cfg.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    path = config_path()
    path.write_text(json.dumps(cfg.to_dict(), indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Tree helpers
# ---------------------------------------------------------------------------


def list_layouts() -> List[Dict[str, Any]]:
    return [
        {
            "name": name,
            "description": meta.get("description") or "",
            "panes": panes_in_tree(meta.get("tree") or {}),
        }
        for name, meta in PRESETS.items()
    ]


def panes_in_tree(node: Dict[str, Any]) -> List[str]:
    if not node:
        return []
    kind = node.get("kind")
    if kind == "leaf":
        pane = node.get("pane")
        return [str(pane)] if pane else []
    out: List[str] = []
    for ch in node.get("children") or []:
        out.extend(panes_in_tree(ch))
    return out


def filter_tree(
    node: Dict[str, Any],
    hidden: Sequence[str],
) -> Optional[Dict[str, Any]]:
    """Drop hidden leaves; collapse empty branches."""
    hidden_set = set(hidden or [])
    kind = node.get("kind")
    if kind == "leaf":
        pane = str(node.get("pane") or "")
        if pane in hidden_set:
            return None
        return dict(node)
    children = []
    ratios = list(node.get("ratio") or [])
    sizes = list(node.get("sizes") or [])
    new_ratios: List[float] = []
    new_sizes: List[Any] = []
    for i, ch in enumerate(node.get("children") or []):
        filtered = filter_tree(ch, hidden_set)
        if filtered is None:
            continue
        children.append(filtered)
        if i < len(ratios):
            new_ratios.append(float(ratios[i]))
        if i < len(sizes):
            new_sizes.append(sizes[i])
    if not children:
        return None
    if len(children) == 1 and kind in {"row", "col"}:
        # collapse single child (preserve leaf size if any)
        only = children[0]
        if only.get("kind") == "leaf" and node.get("size"):
            only = dict(only)
            only["size"] = node.get("size")
        return only
    out = dict(node)
    out["children"] = children
    if new_ratios:
        # renormalize positive ratios
        s = sum(r for r in new_ratios if r > 0) or 1.0
        out["ratio"] = [r / s if r > 0 else 0 for r in new_ratios]
    if new_sizes:
        out["sizes"] = new_sizes
    return out


def apply_ratio_overrides(
    node: Dict[str, Any],
    overrides: Dict[str, List[float]],
) -> Dict[str, Any]:
    """Apply ratio_overrides keyed by 'paneA:paneB:…' for direct children leaves."""
    if not overrides:
        return node
    kind = node.get("kind")
    if kind in {"row", "col"}:
        children = [apply_ratio_overrides(c, overrides) for c in (node.get("children") or [])]
        key_parts = []
        for c in children:
            if c.get("kind") == "leaf":
                key_parts.append(str(c.get("pane")))
            else:
                key_parts.append("*")
        key = ":".join(key_parts)
        out = dict(node)
        out["children"] = children
        if key in overrides and len(overrides[key]) == len(children):
            out["ratio"] = [float(x) for x in overrides[key]]
        # also try left:right style for 2-pane
        if len(children) == 2 and all(c.get("kind") == "leaf" for c in children):
            k2 = f"{children[0].get('pane')}:{children[1].get('pane')}"
            if k2 in overrides:
                out["ratio"] = [float(x) for x in overrides[k2]]
        return out
    return dict(node)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _placeholder(pane: str, focus: str, cfg: SplitPaneConfig) -> Panel:
    focused = pane == focus
    border = cfg.border_focused if focused else cfg.border_normal
    title = PANE_TITLES.get(pane, pane)
    if focused:
        title = f"▸ {title}"
    return Panel(
        Text(f"({pane})", style="dim"),
        title=title,
        border_style=border,
    )


def wrap_pane(
    pane: str,
    content: Optional[RenderableType],
    cfg: SplitPaneConfig,
) -> Panel:
    focused = pane == cfg.focus
    border = cfg.border_focused if focused else (
        "yellow" if pane in {"tools", "events"} else cfg.border_normal
    )
    if pane == "header":
        border = "cyan"
    if pane == "status":
        border = "blue"
    title = PANE_TITLES.get(pane, pane)
    if focused:
        title = f"▸ {title}"
    body: RenderableType = content if content is not None else Text(
        f"({pane} empty)", style="dim"
    )
    # If content is already a Panel, use its renderable to avoid double borders
    if isinstance(body, Panel):
        body = body.renderable
        if body is None:
            body = Text(f"({pane})", style="dim")
    return Panel(body, title=title, border_style=border)


def _build_layout_node(
    node: Dict[str, Any],
    contents: Dict[str, RenderableType],
    cfg: SplitPaneConfig,
    name: str = "root",
) -> Layout:
    kind = node.get("kind")
    if kind == "leaf":
        pane = str(node.get("pane") or "messages")
        size = node.get("size")
        lay = Layout(name=pane, size=int(size) if size else None)
        lay.update(wrap_pane(pane, contents.get(pane), cfg))
        return lay

    children_nodes = node.get("children") or []
    ratios = list(node.get("ratio") or [1] * len(children_nodes))
    sizes = list(node.get("sizes") or [])
    # pad ratios
    while len(ratios) < len(children_nodes):
        ratios.append(1.0)

    child_layouts: List[Layout] = []
    for i, ch in enumerate(children_nodes):
        cname = f"{name}.{i}"
        if ch.get("kind") == "leaf":
            cname = str(ch.get("pane") or cname)
        size = None
        if i < len(sizes) and sizes[i] is not None:
            size = int(sizes[i])
        elif ch.get("size"):
            size = int(ch["size"])
        # ratio for flexible children
        ratio = int(max(1, round(float(ratios[i]) * 100))) if size is None else None
        if size is not None:
            sub = _build_layout_node(ch, contents, cfg, cname)
            # force size on outer wrapper
            sub.size = size
            child_layouts.append(sub)
        else:
            sub = _build_layout_node(ch, contents, cfg, cname)
            sub.ratio = max(1, int(round(float(ratios[i]) * 10)) or 1)
            child_layouts.append(sub)

    root = Layout(name=name)
    if kind == "row":
        root.split_row(*child_layouts)
    else:
        root.split_column(*child_layouts)
    return root


def build_layout(
    contents: Optional[Dict[str, RenderableType]] = None,
    *,
    cfg: Optional[SplitPaneConfig] = None,
) -> Layout:
    """Build a Rich Layout from config + per-pane renderables."""
    cfg = cfg or load_config()
    contents = contents or {}
    meta = PRESETS.get(cfg.layout) or PRESETS[DEFAULT_LAYOUT]
    tree = meta.get("tree") or {"kind": "leaf", "pane": "messages"}
    tree = apply_ratio_overrides(tree, cfg.ratio_overrides)
    filtered = filter_tree(tree, cfg.hidden)
    if filtered is None:
        # everything hidden — show focus placeholder
        filtered = {"kind": "leaf", "pane": cfg.focus if cfg.focus in PANE_IDS else "messages"}
    return _build_layout_node(filtered, contents, cfg)


def layout_summary(cfg: Optional[SplitPaneConfig] = None) -> Dict[str, Any]:
    cfg = cfg or load_config()
    meta = PRESETS.get(cfg.layout) or PRESETS[DEFAULT_LAYOUT]
    tree = filter_tree(
        apply_ratio_overrides(meta.get("tree") or {}, cfg.ratio_overrides),
        cfg.hidden,
    )
    panes = panes_in_tree(tree or {})
    return {
        "ok": True,
        "layout": cfg.layout,
        "description": meta.get("description"),
        "focus": cfg.focus,
        "hidden": list(cfg.hidden),
        "visible_panes": panes,
        "ratio_overrides": dict(cfg.ratio_overrides),
        "presets": list(PRESETS.keys()),
        "config_path": str(config_path()),
    }


# ---------------------------------------------------------------------------
# Config mutations (slash commands)
# ---------------------------------------------------------------------------


def set_layout(name: str, *, cfg: Optional[SplitPaneConfig] = None, persist: bool = True) -> Dict[str, Any]:
    from .spend_guard import ensure_public_result

    cfg = cfg or load_config()
    name = (name or "").strip().lower()
    aliases = {
        "h": "h-split",
        "horizontal": "h-split",
        "v": "v-split",
        "vertical": "v-split",
        "side": "classic",
        "side-by-side": "classic",
        "default": "agent",
        "2x2": "quad",
        "3": "triple",
    }
    name = aliases.get(name, name)
    if name not in PRESETS:
        return ensure_public_result(
            {
                "ok": False,
                "error": "unknown_layout",
                "name": name,
                "available": list(PRESETS.keys()),
            },
            ok=False,
        )
    cfg.layout = name
    # ensure focus is visible in new layout
    visible = panes_in_tree(PRESETS[name]["tree"])
    visible = [p for p in visible if p not in cfg.hidden]
    if cfg.focus not in visible and visible:
        cfg.focus = visible[0]
    if persist:
        save_config(cfg)
    return ensure_public_result(
        {"ok": True, "layout": cfg.layout, **layout_summary(cfg)},
        ok=True,
    )


def set_focus(pane: str, *, cfg: Optional[SplitPaneConfig] = None, persist: bool = True) -> Dict[str, Any]:
    from .spend_guard import ensure_public_result

    cfg = cfg or load_config()
    pane = (pane or "").strip().lower()
    if pane not in PANE_IDS:
        return ensure_public_result(
            {"ok": False, "error": "unknown_pane", "pane": pane, "available": list(PANE_IDS)},
            ok=False,
        )
    if pane in cfg.hidden:
        cfg.hidden = [h for h in cfg.hidden if h != pane]
    cfg.focus = pane
    if persist:
        save_config(cfg)
    return ensure_public_result(
        {"ok": True, "focus": cfg.focus, "hidden": list(cfg.hidden)},
        ok=True,
    )


def cycle_focus(*, cfg: Optional[SplitPaneConfig] = None, persist: bool = True) -> Dict[str, Any]:
    cfg = cfg or load_config()
    summary = layout_summary(cfg)
    visible = summary.get("visible_panes") or ["messages"]
    if not visible:
        visible = ["messages"]
    try:
        idx = visible.index(cfg.focus)
        nxt = visible[(idx + 1) % len(visible)]
    except ValueError:
        nxt = visible[0]
    return set_focus(nxt, cfg=cfg, persist=persist)


def hide_pane(pane: str, *, cfg: Optional[SplitPaneConfig] = None, persist: bool = True) -> Dict[str, Any]:
    from .spend_guard import ensure_public_result

    cfg = cfg or load_config()
    pane = (pane or "").strip().lower()
    if pane not in PANE_IDS:
        return ensure_public_result(
            {"ok": False, "error": "unknown_pane", "pane": pane},
            ok=False,
        )
    if pane not in cfg.hidden:
        cfg.hidden.append(pane)
    # move focus if needed
    vis = [p for p in panes_in_tree((PRESETS.get(cfg.layout) or PRESETS[DEFAULT_LAYOUT])["tree"]) if p not in cfg.hidden]
    if cfg.focus == pane and vis:
        cfg.focus = vis[0]
    if persist:
        save_config(cfg)
    return ensure_public_result(
        {"ok": True, "hidden": list(cfg.hidden), "focus": cfg.focus},
        ok=True,
    )


def show_pane(pane: str, *, cfg: Optional[SplitPaneConfig] = None, persist: bool = True) -> Dict[str, Any]:
    from .spend_guard import ensure_public_result

    cfg = cfg or load_config()
    pane = (pane or "").strip().lower()
    if pane not in PANE_IDS:
        return ensure_public_result(
            {"ok": False, "error": "unknown_pane", "pane": pane},
            ok=False,
        )
    cfg.hidden = [h for h in cfg.hidden if h != pane]
    if persist:
        save_config(cfg)
    return ensure_public_result(
        {"ok": True, "hidden": list(cfg.hidden), "shown": pane},
        ok=True,
    )


def set_ratio(
    spec: str,
    *,
    cfg: Optional[SplitPaneConfig] = None,
    persist: bool = True,
) -> Dict[str, Any]:
    """
    Set ratio override.

    Forms:
      - "3:1"           → messages:tools (default pair for classic)
      - "messages:tools=3:1"
      - "3:1:1"         → first three leaf row in current layout if triple
    """
    from .spend_guard import ensure_public_result

    cfg = cfg or load_config()
    spec = (spec or "").strip()
    if not spec:
        return ensure_public_result({"ok": False, "error": "empty_ratio"}, ok=False)

    key = "messages:tools"
    ratios_part = spec
    if "=" in spec:
        key, ratios_part = spec.split("=", 1)
        key = key.strip()
        ratios_part = ratios_part.strip()
    elif ":" in spec and not any(c.isalpha() for c in spec.split(":")[0]):
        # pure numbers like 3:1 or 3:1:1
        parts_num = ratios_part.split(":")
        try:
            nums = [float(x) for x in parts_num]
        except ValueError:
            return ensure_public_result({"ok": False, "error": "bad_ratio", "spec": spec}, ok=False)
        if len(nums) == 2:
            key = "messages:tools"
        elif len(nums) == 3:
            key = "messages:tools:events"
        else:
            key = ":".join([f"p{i}" for i in range(len(nums))])
        cfg.ratio_overrides[key] = nums
        if persist:
            save_config(cfg)
        return ensure_public_result(
            {"ok": True, "key": key, "ratio": nums, "overrides": dict(cfg.ratio_overrides)},
            ok=True,
        )

    try:
        nums = [float(x) for x in ratios_part.split(":") if x.strip() != ""]
    except ValueError:
        return ensure_public_result({"ok": False, "error": "bad_ratio", "spec": spec}, ok=False)
    if not nums or any(n < 0 for n in nums):
        return ensure_public_result({"ok": False, "error": "bad_ratio", "spec": spec}, ok=False)
    cfg.ratio_overrides[key] = nums
    if persist:
        save_config(cfg)
    return ensure_public_result(
        {"ok": True, "key": key, "ratio": nums, "overrides": dict(cfg.ratio_overrides)},
        ok=True,
    )


def reset_config(*, persist: bool = True) -> Dict[str, Any]:
    from .spend_guard import ensure_public_result

    cfg = SplitPaneConfig()
    if persist:
        save_config(cfg)
    return ensure_public_result({"ok": True, **layout_summary(cfg)}, ok=True)


# ---------------------------------------------------------------------------
# Slash command dispatch
# ---------------------------------------------------------------------------

SPLIT_HELP = """
### Split-pane commands (N209)

| Command | Action |
|---------|--------|
| `/layout [name]` | Show or set layout preset |
| `/split h\\|v\\|classic\\|triple\\|quad\\|agent\\|ide\\|focus` | Shortcut for layout |
| `/focus <pane>` | Focus a pane (highlight border) |
| `/cycle` | Focus next visible pane |
| `/hide <pane>` | Hide pane and reflow |
| `/show <pane>` | Show a hidden pane |
| `/ratio 3:1` | Override messages:tools ratio |
| `/ratio messages:tools=2:1` | Named ratio override |
| `/panes` | List visible / hidden panes |
| `/layouts` | List all presets |
| `/split-status` | Current layout summary JSON |
| `/split-reset` | Reset layout preferences |

Panes: `header` `messages` `tools` `events` `cost` `sessions` `changeset` `help` `status`
"""


def handle_split_slash(
    cmd: str,
    arg: str = "",
    *,
    cfg: Optional[SplitPaneConfig] = None,
    persist: bool = True,
) -> Dict[str, Any]:
    """
    Handle split-pane slash commands.

    Returns dict with ok, and optionally:
      - handled: False if not a split command
      - help / print / summary for the TUI to display
    """
    from .spend_guard import ensure_public_result

    cfg = cfg or load_config()
    c = (cmd or "").strip().lower().lstrip("/")
    a = (arg or "").strip()

    if c in {"layout"}:
        if not a:
            return ensure_public_result(
                {"ok": True, "handled": True, "summary": layout_summary(cfg)},
                ok=True,
            )
        return {**set_layout(a, cfg=cfg, persist=persist), "handled": True}

    if c in {"split"}:
        if not a:
            return ensure_public_result(
                {
                    "ok": True,
                    "handled": True,
                    "help": "Usage: /split h|v|classic|triple|quad|agent|ide|focus",
                    "summary": layout_summary(cfg),
                },
                ok=True,
            )
        return {**set_layout(a, cfg=cfg, persist=persist), "handled": True}

    if c in {"focus"}:
        if not a:
            return ensure_public_result(
                {"ok": True, "handled": True, "focus": cfg.focus, "panes": list(PANE_IDS)},
                ok=True,
            )
        return {**set_focus(a, cfg=cfg, persist=persist), "handled": True}

    if c in {"cycle", "next-pane", "tab"}:
        return {**cycle_focus(cfg=cfg, persist=persist), "handled": True}

    if c in {"hide"}:
        if not a:
            return ensure_public_result(
                {"ok": False, "handled": True, "error": "usage: /hide <pane>"},
                ok=False,
            )
        return {**hide_pane(a, cfg=cfg, persist=persist), "handled": True}

    if c in {"show"}:
        if not a:
            return ensure_public_result(
                {"ok": False, "handled": True, "error": "usage: /show <pane>"},
                ok=False,
            )
        return {**show_pane(a, cfg=cfg, persist=persist), "handled": True}

    if c in {"ratio"}:
        return {**set_ratio(a, cfg=cfg, persist=persist), "handled": True}

    if c in {"panes"}:
        s = layout_summary(cfg)
        return ensure_public_result(
            {
                "ok": True,
                "handled": True,
                "visible": s["visible_panes"],
                "hidden": s["hidden"],
                "focus": s["focus"],
                "all": list(PANE_IDS),
            },
            ok=True,
        )

    if c in {"layouts"}:
        return ensure_public_result(
            {"ok": True, "handled": True, "layouts": list_layouts()},
            ok=True,
        )

    if c in {"split-status", "splitstatus", "layout-status"}:
        return ensure_public_result(
            {"ok": True, "handled": True, "summary": layout_summary(cfg)},
            ok=True,
        )

    if c in {"split-reset", "splitreset", "layout-reset"}:
        return {**reset_config(persist=persist), "handled": True}

    if c in {"split-help", "splithelp"}:
        return ensure_public_result(
            {"ok": True, "handled": True, "help": SPLIT_HELP},
            ok=True,
        )

    return ensure_public_result({"ok": True, "handled": False}, ok=True)


SPLIT_COMMANDS = {
    "layout",
    "split",
    "focus",
    "cycle",
    "next-pane",
    "tab",
    "hide",
    "show",
    "ratio",
    "panes",
    "layouts",
    "split-status",
    "splitstatus",
    "layout-status",
    "split-reset",
    "splitreset",
    "layout-reset",
    "split-help",
    "splithelp",
}


# ---------------------------------------------------------------------------
# Content builders (agent TUI integration)
# ---------------------------------------------------------------------------


def content_from_agent_state(
    *,
    state: Any = None,
    events: Optional[List[Dict[str, Any]]] = None,
    tools_info: Optional[List[Dict[str, str]]] = None,
    stream_on: bool = True,
    status: str = "",
    changeset_summary: Optional[Dict[str, Any]] = None,
    sessions: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, RenderableType]:
    """Build pane contents from agent session state (duck-typed)."""
    events = events or []
    tools_info = tools_info or []
    msgs = getattr(state, "messages", None) or []
    sid = getattr(state, "id", "?")
    agent = getattr(state, "agent", "?")
    model = getattr(state, "model", None) or "auto"
    perm = getattr(state, "permission", "?")
    cost = float(getattr(state, "estimated_cost_usd", 0) or 0)
    tokens = int(getattr(state, "tokens", 0) or 0)

    # header
    header = Text.from_markup(
        f"[bold cyan]SuperAI[/bold cyan]  "
        f"session=[yellow]{sid}[/yellow]  "
        f"agent=[green]{agent}[/green]  "
        f"model=[magenta]{model}[/magenta]  "
        f"perm=[blue]{perm}[/blue]  "
        f"stream={'on' if stream_on else 'off'}"
    )

    # messages
    mblocks: List[RenderableType] = []
    for m in list(msgs)[-10:]:
        role = str(m.get("role") or "")
        content = str(m.get("content") or "")[:500]
        style = "bold green" if role == "assistant" else "bold white"
        mblocks.append(Text(f"{role}> ", style=style))
        mblocks.append(Text(content + "\n", style="dim" if role == "user" else ""))
        for p in m.get("parts") or []:
            if p.get("type") == "tool_call":
                mblocks.append(
                    Text(
                        f"  ⚙ {p.get('name')} "
                        f"{json.dumps(p.get('arguments') or {})[:70]}\n",
                        style="yellow",
                    )
                )
            if p.get("type") == "tool_result":
                mblocks.append(
                    Text(
                        f"  → ok={p.get('ok')}\n",
                        style="green" if p.get("ok") else "red",
                    )
                )
    messages_body: RenderableType = (
        Group(*mblocks) if mblocks else Text("(no messages — type a task)", style="dim")
    )

    # tools
    ttable = Table(show_header=True, expand=True, box=None, padding=(0, 1))
    ttable.add_column("tool", style="cyan")
    ttable.add_column("desc", style="dim")
    for t in (tools_info or [])[:10]:
        ttable.add_row(str(t.get("name") or ""), str(t.get("desc") or "")[:36])
    if not tools_info:
        ttable.add_row("—", "no tools loaded")

    # events
    elines = []
    for e in events[-12:]:
        detail = {k: v for k, v in e.items() if k not in {"kind", "ts"}}
        elines.append(f"{e.get('kind')}: {json.dumps(detail, default=str)[:55]}")
    events_body: RenderableType = Text(
        "\n".join(elines) if elines else "(events appear here)",
        style="dim",
    )

    # cost
    cost_body = Text(
        f"cost ≈ ${cost:.6f}\ntokens = {tokens}\nmsgs = {len(msgs)}\nstream = {stream_on}"
    )

    # sessions
    if sessions:
        st = Table(show_header=True, expand=True, box=None)
        st.add_column("id")
        st.add_column("agent")
        st.add_column("msgs")
        for r in sessions[:8]:
            st.add_row(
                str(r.get("id") or "")[:12],
                str(r.get("agent") or ""),
                str(r.get("messages") or ""),
            )
        sessions_body: RenderableType = st
    else:
        sessions_body = Text("(use /sessions)", style="dim")

    # changeset
    if changeset_summary:
        changeset_body: RenderableType = Text(
            json.dumps(changeset_summary, indent=2, default=str)[:800],
            style="dim",
        )
    else:
        changeset_body = Text("(no staged changes)", style="dim")

    help_body = Text(SPLIT_HELP.strip()[:1200], style="dim")

    status_body = Text(
        f"cost≈${cost:.6f}  tokens={tokens}  msgs={len(msgs)}  {status}"
    )

    return {
        "header": header,
        "messages": messages_body,
        "tools": ttable,
        "events": events_body,
        "cost": cost_body,
        "sessions": sessions_body,
        "changeset": changeset_body,
        "help": help_body,
        "status": status_body,
    }


def render_split_frame(
    *,
    state: Any = None,
    events: Optional[List[Dict[str, Any]]] = None,
    tools_info: Optional[List[Dict[str, str]]] = None,
    stream_on: bool = True,
    status: str = "",
    changeset_summary: Optional[Dict[str, Any]] = None,
    sessions: Optional[List[Dict[str, Any]]] = None,
    cfg: Optional[SplitPaneConfig] = None,
) -> Layout:
    """High-level: agent state → split Layout."""
    cfg = cfg or load_config()
    contents = content_from_agent_state(
        state=state,
        events=events,
        tools_info=tools_info,
        stream_on=stream_on,
        status=status,
        changeset_summary=changeset_summary,
        sessions=sessions,
    )
    return build_layout(contents, cfg=cfg)


def demo_frame(*, layout: str = "agent") -> Layout:
    """Static demo layout for CLI / tests."""
    cfg = SplitPaneConfig(layout=layout, focus="messages")

    class _S:
        id = "demo-session"
        agent = "build"
        model = "mock"
        permission = "plan"
        messages = [
            {"role": "user", "content": "Explain split-pane TUI"},
            {
                "role": "assistant",
                "content": "N209 provides multi-pane layouts with focus and ratios.",
            },
        ]
        estimated_cost_usd = 0.0
        tokens = 0

    return render_split_frame(
        state=_S(),
        events=[{"kind": "demo", "msg": "hello"}],
        tools_info=[{"name": "read", "desc": "read file"}, {"name": "grep", "desc": "search"}],
        stream_on=True,
        status="demo",
        cfg=cfg,
    )


def status_public() -> Dict[str, Any]:
    from .spend_guard import ensure_public_result

    return ensure_public_result(layout_summary(), ok=True)
