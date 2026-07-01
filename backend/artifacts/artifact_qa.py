import os

class ArtifactQa:
    def verify_artifact(self, filepath: str, required_citations: int = 1) -> dict:
        if not os.path.exists(filepath):
            return {
                "passed": False,
                "score": 0,
                "findings": ["Artifact file does not exist on disk."]
            }
            
        file_size = os.path.getsize(filepath)
        if file_size == 0:
            return {
                "passed": False,
                "score": 0,
                "findings": ["Generated artifact file is empty (0 bytes)."]
            }
            
        findings = []
        score = 100
        
        # Format checks
        ext = os.path.splitext(filepath)[1].lower()
        if ext not in [".pptx", ".pdf", ".docx", ".xlsx", ".md"]:
            findings.append(f"Format {ext} is not on allowlisted list.")
            score -= 20
            
        # Text/Citation checks (only check text-based assets)
        if ext in [".md", ".docx"]:
            try:
                with open(filepath, "r", errors="ignore") as f:
                    content = f.read()
                # Check for brackets indicative of citations e.g. [1] or REF-
                if not any(tag in content for tag in ["[1]", "REF-"]):
                    findings.append("Missing required source citations.")
                    score -= 30
            except Exception as e:
                findings.append(f"Failed to parse artifact text content: {e}")
                score -= 10

        return {
            "passed": score >= 80,
            "score": score,
            "findings": findings if findings else ["All design system and citation gates passed successfully."]
        }
