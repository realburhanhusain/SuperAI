import re
import uuid
import hashlib
from typing import List, Tuple

HIGH_RISK_PATTERNS = [
    r"rm\s+-r[fF]",
    r"DROP\s+TABLE",
    r"git\s+reset\s+--hard"
]

class SimultaneousLaunchButton:
    """
    SLB requires cryptographic approval from two distinct entities before 
    allowing a high-risk command to proceed.
    """
    def __init__(self):
        self.approvals = set()
        self._nonce = str(uuid.uuid4())

    def request_approval(self, command: str) -> str:
        return f"SLB triggered for command: {command}. Nonce: {self._nonce}. Two approvals required."

    def submit_approval(self, entity_id: str, signature: str) -> bool:
        # Dummy cryptographic check
        expected_sig = hashlib.sha256(f"{entity_id}:{self._nonce}".encode()).hexdigest()
        if signature == expected_sig:
            self.approvals.add(entity_id)
            return True
        return False

    def is_unlocked(self) -> bool:
        return len(self.approvals) >= 2


class DestructiveCommandGuard:
    """
    Intercepts shell commands and checks them against high-risk patterns.
    """
    def __init__(self):
        self.risk_patterns = [re.compile(p) for p in HIGH_RISK_PATTERNS]
        self.active_slbs = {}

    def intercept(self, command: str) -> Tuple[bool, str]:
        for pattern in self.risk_patterns:
            if pattern.search(command):
                slb = SimultaneousLaunchButton()
                slb_id = str(uuid.uuid4())
                self.active_slbs[slb_id] = slb
                return False, f"Blocked. {slb.request_approval(command)} SLB ID: {slb_id}"
        
        return True, "Allowed"

    def approve_command(self, slb_id: str, entity_id: str, signature: str) -> str:
        if slb_id not in self.active_slbs:
            return "Invalid SLB ID"
        
        slb = self.active_slbs[slb_id]
        if slb.submit_approval(entity_id, signature):
            if slb.is_unlocked():
                del self.active_slbs[slb_id]
                return "SLB unlocked. Command may proceed."
            return f"Approval accepted. Current approvals: {len(slb.approvals)}/2"
        return "Invalid signature"
