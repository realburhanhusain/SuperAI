# Contributing to SuperAI

Thank you for your interest in contributing to **SuperAI**!  
We welcome contributions from everyone — whether it's bug reports, feature suggestions, documentation improvements, or code changes.

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Enhancements](#suggesting-enhancements)

---

## Code of Conduct

SuperAI follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).  
By participating, you are expected to uphold this code. Please report unacceptable behavior to the maintainers.

---

## How Can I Contribute?

You can contribute in many ways:

- **Report bugs** — Open an issue with clear reproduction steps.
- **Suggest new features** — Describe the problem and proposed solution.
- **Improve documentation** — Fix typos, clarify sections, or add examples.
- **Write code** — Fix bugs or implement new features.
- **Review pull requests** — Help review and test changes from others.

---

## Development Setup (SuperAI)

```powershell
cd C:\Users\burhan.husain\Documents\Personal\github\SuperAI
pip install -e ".[dev]"
pytest -q
```

**Always resume from `TASKBOARD.md`** (and latest `docs/checkpoints/`).  
Implementation tracks A–J are complete in code. Remaining board items are **deferred smoke** (API keys, live bots, rclone, Pages) unless new features are filed.
```powershell
# After a meaningful change:
powershell -File scripts\checkpoint.ps1 -Label "my-change"
```

## Development Setup (generic)


### 1. Fork and Clone the Repository

```bash
git clone https://github.com/your-username/superai.git
cd superai
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate
```

### 3. Install in Development Mode

```bash
pip install -e ".[dev]"
```

This installs all dependencies including development tools (testing, linting, etc.).

### 4. Verify Installation

```bash
superai --help
```

---

## Coding Standards

We follow these guidelines to keep the codebase clean and consistent:

- **Python Style**: Follow [PEP 8](https://peps.python.org/pep-0008/) and use `black` + `isort` for formatting.
- **Type Hints**: Use type hints wherever possible (`from __future__ import annotations`).
- **Docstrings**: Use Google-style or NumPy-style docstrings.
- **Error Handling**: Prefer explicit and informative error messages.
- **Testing**: Add tests for new features and bug fixes (we use `pytest`).
- **CLI Commands**: Use `typer` consistently and follow existing command patterns.

Run the following before submitting a PR:

```bash
black .
isort .
pytest
```

---

## Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification.

**Format:**

```
<type>(<scope>): <short summary>

<body>

<footer>
```

**Common types:**
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**

```
feat(router): add latency-based load balancing strategy

fix(backup): handle encryption key missing gracefully

docs(readme): update installation instructions
```

---

## Pull Request Process

1. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **Make your changes** and commit them with clear messages.

3. **Push your branch**:
   ```bash
   git push origin feat/your-feature-name
   ```

4. **Open a Pull Request** on GitHub targeting the `main` branch.

5. **PR Requirements**:
   - All tests must pass
   - Code must be formatted with `black` and `isort`
   - New features should include tests
   - Update documentation if needed
   - Keep PRs focused (one feature/fix per PR)

6. A maintainer will review your PR. Be responsive to feedback.

---

## Reporting Bugs

When reporting a bug, please include:

- SuperAI version (`superai --version`)
- Python version
- Operating system
- Steps to reproduce the issue
- Expected behavior vs actual behavior
- Any relevant logs or error messages

Use the **Bug Report** template when opening an issue.

---

## Suggesting Enhancements

We love new ideas! When suggesting a feature:

- Clearly describe the problem it solves
- Explain why existing solutions are insufficient
- Provide examples of how it would be used
- If possible, suggest an implementation approach

Use the **Feature Request** template.

---

## Questions?

If you have questions about contributing, feel free to:

- Open a **Discussion** on GitHub
- Ask in an existing issue or pull request

---

Thank you for helping make **SuperAI** better! 🚀

We appreciate every contribution, big or small.