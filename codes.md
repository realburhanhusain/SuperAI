# SuperAI - Consolidated Existing Code

**Purpose**:  
This document consolidates **all code that was actually written** during the development conversation.  
It is meant to be used **together with `implementation_plan.md`** so that future AI implementations do not have to rewrite code that already exists.

**Important Note**:  
Much of the advanced functionality discussed (full LearningEngine, SkillsManager, SecureBackup, ModelRouter, etc.) was only **described** but not fully implemented as complete, working files. Only the code blocks shown below were actually provided in previous responses.

---

## 1. Project Configuration

### `pyproject.toml`

```toml
[project]
name = "superai"
version = "1.0.0"
description = "SuperAI - Intelligent Multi-Model AI Orchestration Platform"
requires-python = ">=3.10"
dependencies = [
    "typer[all]>=0.9",
    "rich>=13.0",
    "pydantic>=2.0",
]

[project.scripts]
superai = "src.superai.cli.main:app"
```

---

## 2. CLI Layer

### `src/superai/cli/main.py`

```python
import typer
from rich.console import Console
from src.superai.core.orchestrator import SuperAIOrchestrator

app = typer.Typer()
console = Console()
orchestrator = SuperAIOrchestrator()

@app.command()
def run(task: str):
    """Run a task with SuperAI"""
    console.print(f"[bold green]SuperAI[/bold green] → {task}")
    result = orchestrator.run_task(task)
    console.print(f"[green]✓[/green] {result['message']}")
    return result

@app.command()
def init():
    """Initialize SuperAI"""
    console.print("[bold green]SuperAI initialized successfully![/bold green]")

@app.command()
def version():
    """Show SuperAI version"""
    console.print("SuperAI v1.0.0 - Phase 1 Core Foundation")

if __name__ == "__main__":
    app()
```

---

## 3. Core Components

### `src/superai/core/config.py`

```python
from pathlib import Path
from typing import Optional
import json

class Config:
    def __init__(self):
        self.home_dir = Path.home() / ".superai"
        self.config_file = self.home_dir / "config.json"
        self.home_dir.mkdir(exist_ok=True)
        
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        if self.config_file.exists():
            with open(self.config_file, "r") as f:
                return json.load(f)
        else:
            default_config = {
                "version": "1.0.0",
                "mock_mode": True,
                "log_level": "INFO",
                "default_model": None
            }
            self._save_config(default_config)
            return default_config
    
    def _save_config(self, config: dict):
        with open(self.config_file, "w") as f:
            json.dump(config, f, indent=2)
    
    def get(self, key: str, default=None):
        return self.config.get(key, default)
    
    def set(self, key: str, value):
        self.config[key] = value
        self._save_config(self.config)
    
    def show(self):
        return self.config


config = Config()
```

### `src/superai/core/logger.py`

```python
import logging
from pathlib import Path
from rich.logging import RichHandler
from datetime import datetime
from rich.console import Console

def get_logger(name: str = "superai") -> logging.Logger:
    """Get a configured logger for SuperAI with both console and file output"""
    
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    
    console_handler = RichHandler(
        rich_tracebacks=True,
        show_time=True,
        show_path=False,
        console=Console()
    )
    console_handler.setLevel(logging.INFO)
    
    log_dir = Path.home() / ".superai" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / f"superai_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    logger.info(f"SuperAI Logger initialized. Log file: {log_file}")
    return logger


logger = get_logger()
```

### `src/superai/core/orchestrator.py` (Improved Version)

```python
from src.superai.core.config import config
from src.superai.core.logger import logger
from rich.console import Console

console = Console()

class SuperAIOrchestrator:
    def __init__(self):
        self.config = config
        self.mock_mode = config.get("mock_mode", True)
        logger.info("SuperAIOrchestrator initialized")
    
    def run_task(self, task: str):
        logger.info(f"Starting task: {task}")
        console.print(f"[bold blue]SuperAI[/bold blue] → {task}")
        
        console.print("[yellow]Step 1:[/yellow] Analyzing task...")
        logger.debug("Analyzing task requirements")
        
        console.print("[yellow]Step 2:[/yellow] Breaking down into steps...")
        steps = ["Understand requirements", "Plan implementation", "Execute core logic", "Review and finalize"]
        
        console.print("[yellow]Step 3:[/yellow] Executing steps...")
        for i, step in enumerate(steps, 1):
            console.print(f"  [{i}/{len(steps)}] {step}")
            logger.debug(f"Executing step {i}: {step}")
        
        logger.info("Task completed successfully")
        console.print("[green]✓ Task completed successfully (Phase 1)[/green]")
        
        return {
            "status": "success",
            "message": "Task completed successfully",
            "steps_completed": len(steps),
            "mode": "mock"
        }
```

---

## 4. Learning & Memory Components (Partial Implementations)

These methods were written as improvements to a `LearningEngine` class. They can be used as reference when implementing `src/superai/core/learning_engine.py`.

### `distill_knowledge()` Method

```python
def distill_knowledge(self, task_type: Optional[str] = None, min_group_size: int = 4) -> Dict:
    """
    Distill knowledge by consolidating redundant/similar learnings into higher-quality insights.
    """
    tags = ["learning"]
    if task_type:
        tags.append(task_type)

    memories = self.memory.retrieve_by_tags(tags, limit=200)

    if len(memories) < min_group_size:
        return {"distilled": False, "message": "Not enough memories to distill."}

    groups = {}
    for mem in memories:
        meta = mem.get("metadata", {})
        key = (meta.get("task_type", "unknown"), meta.get("model", "unknown"))
        if key not in groups:
            groups[key] = []
        groups[key].append(mem)

    distilled_groups = 0
    total_deprecated = 0

    for key, mem_list in groups.items():
        if len(mem_list) >= min_group_size:
            mem_list.sort(key=lambda x: x.get("importance", 0.5), reverse=True)
            main_memory = mem_list[0]
            for redundant in mem_list[1:]:
                redundant["metadata"]["deprecated"] = True
                redundant["metadata"]["deprecated_reason"] = "Redundant learning - distilled into higher-quality version"
                redundant["metadata"]["consolidated_into"] = main_memory.get("id")
                redundant["importance"] = max(0.05, redundant.get("importance", 0.5) * 0.3)
                total_deprecated += 1
            distilled_groups += 1

    return {
        "distilled": True,
        "groups_analyzed": len(groups),
        "groups_distilled": distilled_groups,
        "memories_deprecated": total_deprecated,
        "message": f"Distilled {distilled_groups} groups and deprecated {total_deprecated} redundant memories."
    }
```

### `resolve_conflicts()` Method (Improved)

```python
def resolve_conflicts(self, auto_resolve: bool = True) -> Dict:
    """
    Detect and resolve conflicting learnings.
    """
    conflicts = self.detect_conflicts()
    resolved = 0
    unresolved = 0

    for conflict in conflicts:
        if auto_resolve:
            memories = self.memory.retrieve_by_tags(["learning"], limit=200)
            group = [
                m for m in memories 
                if m.get("metadata", {}).get("task_type") == conflict["task_type"]
                and m.get("metadata", {}).get("model") == conflict["model"]
            ]

            if len(group) >= 2:
                group.sort(key=lambda x: x.get("importance", 0.5), reverse=True)
                winner = group[0]

                for loser in group[1:]:
                    loser["metadata"]["deprecated"] = True
                    loser["metadata"]["deprecated_reason"] = "Resolved conflict - lower confidence"
                    loser["metadata"]["resolved_into"] = winner.get("id")
                    loser["importance"] = max(0.05, loser.get("importance", 0.5) * 0.3)
                resolved += 1
            else:
                unresolved += 1
        else:
            unresolved += 1

    return {
        "conflicts_found": len(conflicts),
        "conflicts_resolved": resolved,
        "conflicts_unresolved": unresolved,
        "message": f"Resolved {resolved} conflicts automatically."
    }
```

### `summarize_knowledge()` Method

```python
def summarize_knowledge(self, query: str, max_memories: int = 10) -> Dict:
    """
    Generate a high-level summary from relevant memories.
    """
    memories = self.memory.query_semantic(query=query, top_k=max_memories)
    
    if not memories:
        return {
            "summary": "No relevant memories found.",
            "count": 0
        }
    
    summary_points = []
    for mem in memories[:max_memories]:
        content = mem.get("content", "")[:200]
        meta = mem.get("metadata", {})
        summary_points.append(f"- {content} (Model: {meta.get('model', 'unknown')})")
    
    return {
        "summary": "\n".join(summary_points),
        "count": len(memories),
        "query": query,
        "message": f"Generated summary from {len(memories)} relevant memories."
    }
```

### `get_relevant_context_for_current_task()` Method (Mid-task Adaptation)

```python
def get_relevant_context_for_current_task(
    self, 
    task_description: str, 
    task_type: Optional[str] = None,
    limit: int = 6
) -> Dict:
    """
    Get relevant past learnings and warnings that can be used during active task execution.
    """
    query = task_description
    if task_type:
        query = f"{task_type} task: {task_description}"

    memories = self.memory.query_semantic(query=query, top_k=limit)

    positive_learnings = []
    warnings = []

    for mem in memories:
        meta = mem.get("metadata", {})
        content = mem.get("content", "")[:350]
        is_success = meta.get("success") is True or "success" in mem.get("tags", [])

        item = {
            "content": content,
            "model": meta.get("model"),
            "task_type": meta.get("task_type")
        }

        if is_success:
            positive_learnings.append(item)
        else:
            warnings.append(item)

    return {
        "relevant_learnings": positive_learnings,
        "warnings": warnings,
        "total_retrieved": len(memories),
        "message": "Use these past experiences to guide the current task."
    }
```

### `track_knowledge_evolution()` Method

```python
def track_knowledge_evolution(self, topic: str) -> Dict:
    """
    Track how the system's understanding of a specific topic has evolved over time.
    """
    memories = self.memory.retrieve_by_tags(["learning"], limit=100)
    
    topic_memories = [
        m for m in memories 
        if topic.lower() in m.get("content", "").lower() 
        or topic.lower() in str(m.get("metadata", {})).lower()
    ]
    
    if len(topic_memories) < 3:
        return {
            "topic": topic,
            "evolution_detected": False,
            "message": "Not enough data to track evolution for this topic."
        }
    
    topic_memories.sort(key=lambda x: x.get("created_at", ""))
    
    evolution_summary = []
    for mem in topic_memories:
        meta = mem.get("metadata", {})
        evolution_summary.append({
            "timestamp": meta.get("created_at"),
            "model": meta.get("model"),
            "key_insight": mem.get("content", "")[:150] + "...",
            "importance": mem.get("importance", 0.5)
        })
    
    return {
        "topic": topic,
        "evolution_detected": True,
        "total_memories": len(topic_memories),
        "evolution_summary": evolution_summary,
        "message": f"Knowledge about '{topic}' has evolved over {len(topic_memories)} memories."
    }
```

---

## Summary of What Exists vs What Needs to Be Built

| Component                    | Status          | Notes |
|-----------------------------|------------------|-------|
| CLI (`main.py`)             | Partially done   | Basic commands exist |
| Config System               | Done             | Usable |
| Logger                      | Done             | Usable |
| Basic Orchestrator          | Partially done   | Mock mode only |
| LearningEngine (methods)    | Partial          | Several key methods written |
| MemoryPalace                | Very basic       | Needs full implementation |
| ModelRegistry / Router      | Not implemented  | Needs to be built from scratch |
| Skills System               | Not implemented  | Needs to be built from scratch |
| Backup System               | Not implemented  | Needs to be built from scratch |
| Dashboards                  | Not implemented  | Needs to be built from scratch |

---

**Recommendation**:  
Use `implementation_plan.md` as the master blueprint and reference this `codes.md` file to reuse existing code instead of rewriting it. Most of the advanced architecture still needs to be implemented from scratch.

This document was created to save time for future AI agents working on the project.
