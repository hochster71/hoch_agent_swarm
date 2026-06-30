import os
import yaml
from backend.brain.data_classifier import DataClassifier

class WorkflowCompiler:
    def __init__(self, root_dir=None):
        from backend.runtime_paths import project_root
        if root_dir is None:
            root_dir = str(project_root())
        self.root_dir = root_dir
        self.classifier = DataClassifier(root_dir)
        self.templates_path = os.path.join(root_dir, "config/workflow_templates.yaml")

    def compile_intent(self, requester: str, text: str) -> dict:
        # 1. Classify the request scope
        class_res = self.classifier.classify_request(requester, text)
        if not class_res["allowed"]:
            return {
                "success": False,
                "error": f"Workflow compilation blocked: {class_res['reason']}",
                "classification": class_res["classification"]
            }

        # 2. Match templates
        text_lower = text.lower()
        workflow_type = "unknown"
        steps = []
        
        if "presentation" in text_lower or "slide" in text_lower or "deck" in text_lower:
            workflow_type = "create_slide_deck"
            steps = [
                "Identify requester and role permission",
                "Classify request and verify data boundaries",
                "Perform RAG retrieval from trusted cybersecurity sources",
                "Apply brand/design system parameters",
                "Generate PPTX structure and export slides",
                "Run QA / citation / design checkers",
                "Generate PDF printable output",
                "Handoff to allowlisted Google Drive path",
                "Generate delivery receipt and audit trail"
            ]
        elif "print" in text_lower or "pdf" in text_lower or "sheet" in text_lower:
            workflow_type = "create_printable_pdf"
            steps = [
                "Identify requester",
                "Retrieve required content layout",
                "Apply brand spacing and design styles",
                "Export to PDF",
                "Handoff to target Google Drive folder",
                "Log transaction and evidence"
            ]
        else:
            workflow_type = "research_current_guidance"
            steps = [
                "Analyze query terms",
                "Query local knowledge indexes",
                "Format executive summary report"
            ]

        return {
            "success": True,
            "workflow_type": workflow_type,
            "classification": class_res["classification"],
            "steps": steps,
            "requester": requester,
            "text": text
        }
