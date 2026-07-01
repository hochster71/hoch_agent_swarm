import os
import tempfile
from backend.brain.workflow_compiler import WorkflowCompiler
from backend.artifacts.slide_factory import SlideFactory
from backend.artifacts.artifact_qa import ArtifactQa
from backend.connectors.google_drive_delivery import GoogleDriveDelivery

def test_full_workflow_integration():
    compiler = WorkflowCompiler()
    
    # 1. Compile intent
    res = compiler.compile_intent("michael", "Generate presentation slide deck on current cybersecurity guidance")
    assert res["success"] is True
    assert res["workflow_type"] == "create_slide_deck"
    
    # 2. Build Slide Deck
    factory = SlideFactory()
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "cyber_brief.pptx")
        slides_content = [
            ("Introduction", ["First compliance point.", "Second compliance point."]),
            ("Deep Dive", ["All data local loopback.", "No external API calls."])
        ]
        
        factory.create_deck("Cyber Brief", "Branded Analysis", slides_content, filepath)
        assert os.path.exists(filepath)
        assert os.path.getsize(filepath) > 0
        
        # 3. QA check
        qa = ArtifactQa()
        qa_res = qa.verify_artifact(filepath)
        assert qa_res["passed"] is True
        assert qa_res["score"] >= 80
        
        # 4. Handoff/Delivery
        delivery = GoogleDriveDelivery()
        del_res = delivery.deliver_file("michael", filepath, "family_shared")
        assert del_res["success"] is True
        assert del_res["receipt_id"].startswith("rcpt-")
        assert del_res["folder"] == "Hoch Family/Shared"
