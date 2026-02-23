import sqlite3
import os
import sys

def get_db_path():
    # Attempt to locate DB from default paths
    paths = ["data/lcp_main.db", "../data/lcp_main.db"]
    for p in paths:
        if os.path.exists(p): return p
    return None

def show_stats():
    path = get_db_path()
    if not path:
        print("❌ Database not found.")
        return
    
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    
    print(f"📊 Database Stats: {path}")
    cursor.execute("SELECT COUNT(*) FROM media_items")
    print(f"- Total Media Items: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM face_records")
    print(f"- Total Face Records: {cursor.fetchone()[0]}")
    
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stats":
        show_stats()
    else:
        print("Usage: python db_utils.py [stats|vacuum|verify]")
