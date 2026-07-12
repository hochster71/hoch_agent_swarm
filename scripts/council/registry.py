import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROSTER = ROOT / "coordination" / "council" / "council_roster.json"
DEFAULT_CONTRACTS = ROOT / "coordination" / "council" / "frontier_seat_contracts.json"

class NotWired(Exception): pass
class ProfileViolation(Exception): pass
class UnknownMember(Exception): pass

class Registry:
    def __init__(self, roster_path=None, contracts_path=None):
        self.roster_path = Path(roster_path or DEFAULT_ROSTER)
        self.contracts_path = Path(contracts_path or DEFAULT_CONTRACTS)

        self.roster = json.loads(self.roster_path.read_text(encoding="utf-8")) if self.roster_path.exists() else {}
        self.contracts = json.loads(self.contracts_path.read_text(encoding="utf-8")) if self.contracts_path.exists() else {}

        self.doc = self.roster  # some places use reg.doc["quorum"]["advisory"]
        self.seats = self.roster.get("members", {s.get("member_id"): s for s in self.roster.get("seats", [])})

    def validate_schema(self):
        errors = []
        if not self.roster:
            errors.append("MISSING_ROSTER")
        if not self.contracts:
            errors.append("MISSING_CONTRACTS")
        return errors

    @property
    def digest(self):
        h = hashlib.sha256()
        h.update(self.roster_path.read_bytes() if self.roster_path.exists() else b"")
        h.update(self.contracts_path.read_bytes() if self.contracts_path.exists() else b"")
        return h.hexdigest()

    def profile(self, name):
        prof = self.roster.get("profiles", {}).get(name)
        if not prof:
            return {"promotion_capable": False, "release_capable": False, "allowed_member_ids": [], "min_quorum": 0}
        return prof

    def required_ids(self, name):
        prof = self.profile(name)
        return prof.get("required_member_ids", [])

    def enabled(self):
        return {k: v for k, v in self.roster.get("members", {}).items() if v.get("enabled", True)}

    def get(self, mid):
        return self.seats.get(mid, {})

    def min_quorum(self, name):
        return self.profile(name).get("min_quorum", 0)

    def resolve_for_dispatch(self, member_id, profile_id):
        mem = self.get(member_id)
        if not mem:
            raise UnknownMember(f"Member not in roster: {member_id}")
        if not mem.get("enabled", True):
            raise ProfileViolation(f"Member disabled: {member_id}")
        prof = self.profile(profile_id)
        if member_id not in prof.get("allowed_member_ids", []):
            raise ProfileViolation(f"Member {member_id} not allowed in profile {profile_id}")

        adapter = mem.get("adapter")
        if not adapter:
            raise NotWired(f"Member {member_id} missing adapter")

        contract = self.contracts.get("seats", {}).get(member_id, {})

        return {
            "member_id": member_id,
            "provider": mem.get("provider", "unknown"),
            "requested_model": mem.get("model", "unknown"),
            "endpoint": mem.get("endpoint", ""),
            "adapter": adapter,
            "schema_version": mem.get("schema_version", "1.0"),
            "timeout_seconds": mem.get("timeout_seconds", 30),
            "auth_source": mem.get("auth_source", ""),
            "contract": contract
        }

    def harness_view(self):
        return {
            "roster": self.roster,
            "contracts": self.contracts,
            "digest": self.digest
        }
