import uuid
import logging
from datetime import datetime
from backend.brain.database import get_db_connection

logger = logging.getLogger("ChatSession")

class ChatSession:
    def __init__(self):
        pass

    def get_or_create_active_session(self) -> str:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM operator_chat_sessions ORDER BY created_at DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return row[0]
            
            # Create a default active session
            session_id = f"session-{str(uuid.uuid4())[:8]}"
            cursor.execute("""
                INSERT INTO operator_chat_sessions (id, created_at, mode, mission_id, summary)
                VALUES (?, ?, 'suggest', 'mission-1', 'Apprenticeship learning mode cockpit')
            """, (session_id, datetime.utcnow().isoformat() + "Z"))
            conn.commit()
            return session_id
        except Exception as e:
            logger.error(f"Error checking active session: {e}")
            return "session-default"
        finally:
            conn.close()

    def get_messages(self, session_id: str) -> list:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT role, content, created_at FROM operator_messages
                WHERE session_id = ?
                ORDER BY created_at ASC
            """, (session_id,))
            rows = cursor.fetchall()
            return [
                {
                    "role": r[0],
                    "content": r[1],
                    "createdAt": r[2]
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
            return []
        finally:
            conn.close()

    def add_message(self, session_id: str, role: str, content: str):
        import uuid
        msg_id = f"msg-{str(uuid.uuid4())[:8]}"
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO operator_messages (id, session_id, role, content, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (msg_id, session_id, role, content, datetime.utcnow().isoformat() + "Z"))
            conn.commit()
        except Exception as e:
            logger.error(f"Error inserting message: {e}")
        finally:
            conn.close()
