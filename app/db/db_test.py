from app.db.connection import get_conn

def main():
    try:
        with get_conn() as conn:
            cur = conn.cursor()

            cur.execute("SELECT DB_NAME()")
            db_name = cur.fetchone()[0]

            cur.execute("SELECT 1")
            one = cur.fetchone()[0]

            print(f"Database connection OK ✅ DB={db_name} Result={one}")
    except Exception as e:
        print("Database connection FAILED ❌")
        print(e)

if __name__ == "__main__":
    main()