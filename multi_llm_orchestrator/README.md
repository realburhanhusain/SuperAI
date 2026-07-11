# SuperAI

**SuperAI** is a powerful, full-featured multi-model AI super app featuring:

- Model-agnostic supervisor with full context loading
- Self-learning Memory Palace (ChromaDB + EmbeddingGemma)
- Automatic skill creation and self-improvement
- Markdown-based Skills system
- External CLI delegation support
- Rich terminal and web dashboards

## Installation

### Prerequisites
- Python 3.11 or higher
- (Optional but recommended) A virtual environment

### Step-by-step Installation

1. **Clone the repository** (or download the source):

```bash
git clone <your-repo-url>
cd multi_llm_orchestrator
```

2. **Create and activate a virtual environment** (recommended):

```bash
python -m venv venv
source venv/bin/activate          # On macOS/Linux
# venv\Scripts\activate           # On Windows
```

3. **Install SuperAI in editable mode**:

```bash
pip install -e .
```

This will automatically install all required dependencies, including:
- `chromadb`
- `sentence-transformers`
- `pydantic`, `typer`, `rich`, etc.

> **Note**: The first time you use EmbeddingGemma or other embedding models, the model weights will be downloaded automatically from Hugging Face.

### Verify Installation

After installation, you can run:

```bash
superai --help
```

Or use it programmatically:

```python
from src.core.memory_palace import MemoryPalace
from src.core.learning_engine import LearningEngine

memory = MemoryPalace(embedding_model="google/embeddinggemma")
engine = LearningEngine(memory)

print("SuperAI initialized successfully!")
```

## Quick Start Example

```python
from src.core.memory_palace import MemoryPalace
from src.core.learning_engine import LearningEngine
from src.core.skills import SkillsManager

# Initialize components
memory = MemoryPalace(embedding_model="google/embeddinggemma")
skills = SkillsManager()
engine = LearningEngine(memory, skills)

# Simulate a completed delegation
delegation = {
    "delegated_to": "claude-code-cli",
    "description": "Implement secure JWT authentication",
    "task_type": "authentication"
}

outcome = {
    "status": "success",
    "confidence": 0.92,
    "notes": "Used proper token rotation and rate limiting"
}

# This automatically stores learning and may create/update skills
engine.learn_from_delegation(delegation, outcome)

print("Learning and skills updated automatically!")
```

## Project Structure

```
src/
├── core/
│   ├── memory_palace.py       # ChromaDB memory with semantic search
│   ├── skills.py              # Skills system with self-improvement
│   ├── learning_engine.py     # Automatic learning + skill creation
│   ├── context_builder.py     # Builds rich supervisor context
│   └── utils.py               # Helper functions
├── cli/
│   └── dashboard.py           # Terminal dashboard (Rich)
└── web/
    └── dashboard_api.py       # Web dashboard (FastAPI)
```

## Key Capabilities

- Any LLM can act as supervisor and load full knowledge
- Automatic persistence of learnings (Mempalace-style hooks)
- Skills evolve over time through self-improvement
- High-performance vector memory with configurable indexing
- Clean separation between memory, skills, and orchestration

SuperAI brings together the best ideas from multi-agent systems, self-improving agents (Hermes), personal assistant skills (OpenClaw), and persistent memory systems.