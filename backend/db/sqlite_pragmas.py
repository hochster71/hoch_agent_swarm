import sqlite3

def apply_wal_pragmas(conn: sqlite3.Connection):
    """Applies Write-Ahead Logging (WAL) and timeout pragmas to SQLite connections."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA busy_timeout=30000;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
