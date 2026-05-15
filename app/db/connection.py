import pyodbc
from contextlib import contextmanager
from app.config.settings import build_connection_string, DEBUG

def _mask_conn_str(conn_str: str) -> str:
    # Mask PWD=... safely
    parts = conn_str.split(";")
    masked = []
    for p in parts:
        if p.upper().startswith("PWD="):
            masked.append("PWD=***")
        else:
            masked.append(p)
    return ";".join(masked)

@contextmanager
def get_conn():
    conn_str = build_connection_string()

    if DEBUG:
        print("DB connection string:", _mask_conn_str(conn_str))

    conn = pyodbc.connect(conn_str, timeout=5)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()