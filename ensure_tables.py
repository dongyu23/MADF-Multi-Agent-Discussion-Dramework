import sqlite3
import os

DB_PATH = "madf.db"
SCHEMA_PATH = "app/db/schema.sql"

def ensure_tables():
    if not os.path.exists(DB_PATH):
        print("Database not found, creating...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
            
        statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
        
        print(f"Executing {len(statements)} schema statements...")
        
        for stmt in statements:
            try:
                cursor.execute(stmt)
            except Exception as e:
                print(f"Error executing statement: {stmt[:50]}... -> {e}")
                
        conn.commit()
        print("Tables check completed.")
    except Exception as e:
        print(f"Failed to read schema or execute: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    ensure_tables()
