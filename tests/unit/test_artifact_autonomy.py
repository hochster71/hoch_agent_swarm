import pytest
import os
import tempfile
from backend.brain.data_classifier import DataClassifier
from backend.rag.source_ranker import SourceRanker
from backend.artifacts.slide_factory import SlideFactory
from backend.connectors.google_drive_delivery import GoogleDriveDelivery

def test_data_classification():
    classifier = DataClassifier()
    
    # Michael should be allowed work internal data
    res = classifier.classify_request("michael", "Review RMF SAIC cybersecurity policy")
    assert res["classification"] == "work internal"
    assert res["allowed"] is True
    
    # Alison should be blocked from work internal data
    res = classifier.classify_request("alison", "Review RMF SAIC cybersecurity policy")
    assert res["classification"] == "work internal"
    assert res["allowed"] is False
    
    # Unknown user should be blocked
    res = classifier.classify_request("unknown", "Any query")
    assert res["classification"] == "restricted"
    assert res["allowed"] is False
    
    # Neutral family request should be allowed for all family
    res = classifier.classify_request("alison", "What chores need to be completed in the pool area?")
    assert res["classification"] == "family"
    assert res["allowed"] is True

def test_source_ranking():
    ranker = SourceRanker()
    ranked = ranker.rank_sources("cybersecurity NIST guidance")
    # Should contain ranked sources
    assert len(ranked) > 0
    # First source should have highest combined score
    assert ranked[0]["relevance_score"] >= ranked[-1]["relevance_score"]

def test_delivery_allowlist():
    delivery = GoogleDriveDelivery()
    
    # Prepare dummy file to deliver
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"dummy data")
        temp_filepath = f.name
        
    try:
        # Invalid folder targets should fail allowlist check
        res = delivery.deliver_file("michael", temp_filepath, "unapproved_random_folder")
        assert res["success"] is False
        assert "not allowlisted" in res["error"]
        
        # Valid allowlist folders should succeed for authorized users
        res = delivery.deliver_file("michael", temp_filepath, "family_shared")
        assert res["success"] is True
        assert res["receipt_id"].startswith("rcpt-")
    finally:
        os.remove(temp_filepath)
