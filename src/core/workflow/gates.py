import subprocess
import os
import logging

logger = logging.getLogger(__name__)

class QualityGate:
    def __init__(self, name: str):
        self.name = name

    def validate(self, context: dict) -> bool:
        raise NotImplementedError

class DiffAwareGate(QualityGate):
    """
    Diff-aware quality gate to ensure agents cannot commit without passing validation.
    Checks for syntax errors in staged Python files and merge conflict markers.
    """
    def __init__(self):
        super().__init__("diff_aware")
        
    def validate(self, context: dict) -> bool:
        try:
            # Check staged files (those about to be committed)
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            # Fail closed. Without this, a failed `git diff` (not a repo, a
            # corrupt index, git misconfigured) yields empty stdout, which
            # reads as "no staged files" and the gate PASSES - a safety gate
            # silently approving a commit it never actually inspected.
            if result.returncode != 0:
                logger.error(
                    "Validation failed: `git diff --cached` exited %s: %s",
                    result.returncode,
                    (result.stderr or "").strip()[:200],
                )
                return False

            files = result.stdout.strip().split("\n") if result.stdout.strip() else []

            if not files:
                logger.info("No staged files found for diff-aware validation.")
                return True
                
            for f in files:
                if not f or not os.path.exists(f):
                    continue
                
                # 1. Syntax check for Python files
                if f.endswith('.py'):
                    try:
                        with open(f, 'r', encoding='utf-8') as file:
                            compile(file.read(), f, 'exec')
                    except SyntaxError as e:
                        logger.error(f"Validation failed: Syntax error in staged file {f}: {e}")
                        return False
                
                # 2. Check for unresolved merge conflict markers
                with open(f, 'r', encoding='utf-8', errors='ignore') as file:
                    content = file.read()
                    if "<<<<<<< HEAD" in content or "=======" in content and ">>>>>>>" in content:
                        logger.error(f"Validation failed: Unresolved merge conflict markers found in {f}")
                        return False
                        
            logger.info("Diff-aware validation passed successfully.")
            return True
        except Exception as e:
            logger.error(f"Error during diff-aware validation: {e}")
            return False

def enforce_commit_validation() -> bool:
    """
    Utility function to run before any agent commit.
    Returns True if the commit is safe, False otherwise.
    """
    gate = DiffAwareGate()
    return gate.validate({})
