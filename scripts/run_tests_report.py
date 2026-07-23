import os
import sys
import pytest
from pathlib import Path

def main():
    os.environ["SUPERAI_MOCK_MODE"] = "1"
    os.environ["SUPERAI_BOARD_SEMANTIC"] = "1"
    
    repo_root = Path(__file__).resolve().parent.parent
    os.chdir(repo_root)
    
    print("Starting full pytest suite in mock mode...")
    sys.exit(pytest.main(["--tb=short", "-v"]))

if __name__ == "__main__":
    main()
