import pytest
from src.core.quota_manager import QuotaManager, QuotaExceededError

def test_set_and_get_budget():
    qm = QuotaManager()
    qm.set_budget("agent1", 100.0)
    assert qm.get_budget("agent1") == 100.0
    assert qm.get_spend("agent1") == 0.0

def test_record_spend():
    qm = QuotaManager()
    qm.set_budget("agent1", 100.0)
    qm.record_spend("agent1", 50.0)
    assert qm.get_spend("agent1") == 50.0

def test_record_spend_exceeds_quota():
    qm = QuotaManager()
    qm.set_budget("agent1", 100.0)
    with pytest.raises(QuotaExceededError):
        qm.record_spend("agent1", 150.0)

def test_record_spend_no_budget():
    qm = QuotaManager()
    with pytest.raises(ValueError):
        qm.record_spend("agent1", 50.0)
