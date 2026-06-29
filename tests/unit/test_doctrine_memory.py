import pytest
import os
from backend.brain.doctrine_memory import DoctrineMemory
from backend.brain.database import init_brain_tables

def test_doctrine_memory_rules():
    init_brain_tables()
    doctrine = DoctrineMemory()
    
    # Assert we can add a rule and fetch it
    rule_id = doctrine.add_learned_rule("Never write paid API keys to codebase", source="feedback", confidence=0.9)
    assert rule_id.startswith("learned-")
    
    rules = doctrine.get_all_rules()
    assert any(r["ruleText"] == "Never write paid API keys to codebase" for r in rules)
