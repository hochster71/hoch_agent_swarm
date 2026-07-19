from __future__ import annotations
import json
import os
from datetime import datetime, timezone
import jsonschema
from backend.audit_factory.models import POAMItem, POAMHistoryItem, Milestone

class POAMEngine:
    def __init__(self, schema_path: str = None):
        self.schema_path = schema_path or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../coordination/audit_factory/schemas/poam.schema.json")
        )
        self.schema = None
        if os.path.exists(self.schema_path):
            with open(self.schema_path, "r") as f:
                self.schema = json.load(f)

    def create_poam_item(
        self,
        finding_ids: list[str],
        owner: str,
        due_date: str,
        severity: str,
        remediation_plan: str
    ) -> POAMItem:
        poam_id = f"POAM-HAF-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{os.urandom(2).hex()}"
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        item = POAMItem(
            poam_id=poam_id,
            finding_ids=finding_ids,
            owner=owner,
            milestones=[
                Milestone(
                    milestone_id="M1",
                    description="Initial triage & analysis",
                    due_date=due_date,
                    status="PENDING"
                )
            ],
            due_date=due_date,
            severity=severity,
            status="OPEN",
            remediation_plan=remediation_plan,
            history=[
                POAMHistoryItem(
                    timestamp=now_str,
                    updated_by="poam_engine",
                    previous_status="NONE",
                    new_status="OPEN",
                    comment="POA&M record generated."
                )
            ]
        )

        if self.schema:
            jsonschema.validate(instance=item.model_dump(), schema=self.schema)
            
        return item

    def transition_status(
        self,
        item: POAMItem,
        new_status: str,
        updated_by: str,
        comment: str,
        retest_success: bool = False
    ) -> bool:
        """Transitions POA&M status while enforcing that CLOSED requires a successful retest."""
        valid_statuses = {"OPEN", "IN_PROGRESS", "BLOCKED", "READY_FOR_RETEST", "CLOSED", "RISK_ACCEPTED", "EXPIRED"}
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid POA&M status: {new_status}")

        if new_status == "CLOSED" and not retest_success:
            # Enforce: "A POA&M item marked CLOSED without successful independent retest must be rejected."
            return False

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        history_item = POAMHistoryItem(
            timestamp=now_str,
            updated_by=updated_by,
            previous_status=item.status,
            new_status=new_status,
            comment=comment
        )
        
        item.history.append(history_item)
        item.status = new_status
        return True
