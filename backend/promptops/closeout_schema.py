class CloseoutSchema:
    def validate_report(self, report_data: dict, schema_type: str) -> bool:
        required_fields = ["status", "evidence_path", "commit_hash"]
        
        for field in required_fields:
            if field not in report_data or not report_data[field]:
                return False
                
        return True
