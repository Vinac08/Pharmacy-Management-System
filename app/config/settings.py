import os
from dotenv import load_dotenv

load_dotenv()

def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()

# Database settings
DB_DRIVER = _get("DB_DRIVER", "ODBC Driver 17 for SQL Server")
DB_SERVER = _get("DB_SERVER", r"localhost\SQLEXPRESS")
DB_DATABASE = _get("DB_DATABASE", "PHARMACY_MANAGEMENT")
DB_USER = _get("DB_USER", "")
DB_PASSWORD = _get("DB_PASSWORD", "")

# If you leave DB_USER empty -> Windows auth is used
USE_WINDOWS_AUTH = (DB_USER == "")

# Debug flag
DEBUG = _get("DEBUG", "0") == "1"

def build_connection_string() -> str:
    parts = [
        f"DRIVER={{{DB_DRIVER}}}",
        f"SERVER={DB_SERVER}",
        f"DATABASE={DB_DATABASE}",
        "TrustServerCertificate=yes",
    ]

    if USE_WINDOWS_AUTH:
        parts.append("Trusted_Connection=yes")
    else:
        parts.append(f"UID={DB_USER}")
        parts.append(f"PWD={DB_PASSWORD}")

    return ";".join(parts) + ";"