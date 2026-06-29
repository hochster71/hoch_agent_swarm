import sqlite3
import logging
from datetime import datetime
from backend.brain.database import get_db_connection

logger = logging.getLogger("ApprovalLearner")

class ApprovalLearner:
    def __init__(self):
        pass

    def record_feedback(self, suggestion_id: str, decision: str, correction: str = None):
        """
        decision: 'approved' or 'rejected'
        """
        import uuid
        feedback_id = f"fb-{str(uuid.uuid4())[:8]}"
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 1. Store feedback
            cursor.execute("""
                INSERT INTO operator_feedback (id, suggestion_id, decision, correction, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (feedback_id, suggestion_id, decision, correction, datetime.utcnow().isoformat() + "Z"))
            
            # 2. If rejected, penalize the confidence of the original suggestion
            if decision == "rejected":
                cursor.execute("""
                    UPDATE brain_suggestions
                    SET confidence = MAX(0.1, confidence - 0.2)
                    WHERE id = ?
                """, (suggestion_id,))
                
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to record operator feedback: {e}")
            conn.rollback()
        finally:
            conn.close()

    def get_prediction_accuracy(self) -> float:
        """
        Computes accuracy: (number of approved suggestions) / (total feedback items)
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT COUNT(*) FROM operator_feedback WHERE decision = 'approved'
            """)
            approved = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM operator_feedback
            """)
            total = cursor.fetchone()[0]
            
            if total == 0:
                return 0.0 # Default to 0% when no feedback has been received yet
                
            return float(approved) / float(total)
        except Exception as e:
            logger.error(f"Error computing prediction accuracy: {e}")
            return 1.0
        finally:
            conn.close()
            
    def get_shadow_logs(self) -> list:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT s.id, s.suggested_action, s.confidence, f.decision, f.created_at
                FROM brain_suggestions s
                LEFT JOIN operator_feedback f ON s.id = f.suggestion_id
                ORDER BY s.created_at DESC
                LIMIT 15
            """)
            rows = cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "suggestedAction": r[1],
                    "confidence": r[2],
                    "decision": r[3] or "PENDING",
                    "createdAt": r[4]
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Error getting shadow logs: {e}")
            return []
        finally:
            conn.close()
