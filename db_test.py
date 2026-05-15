from app.db.connection import get_conn 
 
try: 
    with get_conn() as conn: 
        cursor = conn.cursor() 
        cursor.execute("SELECT 1") 
        row = cursor.fetchone() 
        print("Database connection OK ✅ Result:", row[0]) 
except Exception as e: 
    print("Database connection FAILED ❌") 
    print(e)
