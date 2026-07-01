import sqlite3
from pathlib import Path

db_path = Path("/Users/michaelhoch/hoch_agent_swarm/backend/swarm_ledger.db")

conn = sqlite3.connect(db_path)
try:
    cursor = conn.cursor()
    cursor.execute("UPDATE runtime_truth_signals SET value = '2' WHERE signal_id = 'critical_gap_count'")
    cursor.execute("UPDATE runtime_truth_signals SET value = '1' WHERE signal_id = 'ownerless_domain_count'")
    cursor.execute("UPDATE runtime_truth_signals SET value = 'BLOCKED' WHERE signal_id = 'final_verifier_status'")
    cursor.execute("UPDATE runtime_truth_signals SET value = '50.0' WHERE signal_id = 'readiness_score'")
    conn.commit()
    print("Injected blockers successfully!")
finally:
    conn.close()
