# Backup, Restore, and Rollback Procedures
import shutil
import os
import sqlite3

def backup_sqlite_database(src_db: str, dest_backup: str) -> bool:
    """
    Safely copies the SQLite database file for snapshots.
    """
    if not os.path.exists(src_db):
        raise FileNotFoundError(f"Source database {src_db} not found")
    shutil.copy2(src_db, dest_backup)
    return os.path.exists(dest_backup)

def validate_backup_schema(backup_db: str) -> bool:
    """
    Runs schema integrity tests on a restored database instance.
    """
    try:
        conn = sqlite3.connect(backup_db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        result = cursor.fetchone()
        conn.close()
        return result[0] == "ok"
    except Exception:
        return False
