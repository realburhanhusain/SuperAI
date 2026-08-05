import os
import json
from pathlib import Path
from core.config import validate_changes, diff_changes, config

def test_config_validate_unknown_key():
    changes = {"not_a_real_key": True}
    errors = validate_changes(changes)
    assert len(errors) == 1
    assert "'not_a_real_key': unknown key" in errors[0]

def test_config_validate_types():
    # bool vs int
    errors = validate_changes({"mock_mode": 1})
    assert len(errors) == 1
    assert "'mock_mode': must be a boolean" in errors[0]
    
    errors = validate_changes({"max_delegation_depth": True})
    assert len(errors) == 1
    assert "'max_delegation_depth': must be an integer" in errors[0]
    
    errors = validate_changes({"budget_daily_usd": True})
    assert len(errors) == 1
    assert "'budget_daily_usd': must be a float" in errors[0]

def test_config_validate_bounds():
    errors = validate_changes({"bandit_epsilon": 1.5})
    assert len(errors) == 1
    assert "'bandit_epsilon': must be between 0.0 and 1.0" in errors[0]
    
    errors = validate_changes({"budget_daily_usd": -5.0})
    assert len(errors) == 1
    assert "'budget_daily_usd': must be >= 0" in errors[0]
    
    errors = validate_changes({"worker_max": 0})
    assert len(errors) == 1
    assert "'worker_max': must be >= 1" in errors[0]

def test_config_validate_valid():
    errors = validate_changes({"mock_mode": False, "budget_daily_usd": 10.0})
    assert len(errors) == 0

def test_config_diff_changes(tmp_path):
    # Set a secret in the current config
    config.set("data_dsn", "postgresql://user:password@host/db", persist=False)
    
    changes = {"mock_mode": not config.use_mock}
    
    # Store mtime
    config_file = config.config_path
    if config_file.exists():
        mtime_before = config_file.stat().st_mtime
    else:
        mtime_before = None
        
    diff = diff_changes(changes)
    
    # Ensure no writes
    if config_file.exists():
        assert config_file.stat().st_mtime == mtime_before
    else:
        assert mtime_before is None
        
    # Check diff output
    assert "current_config" in diff
    assert "proposed_config" in diff
    
    # Check redaction
    assert "password" not in diff
    assert "REDACTED" in diff or "postgresql://user:password@host/db" not in diff
