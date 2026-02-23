import sqlite3
import json

db_path = "data/curator.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT file_path, tags, character_tags, series_tags FROM files")
for row in cur.fetchall():
    print("File:", row[0])
    print("  General Tags:", json.loads(row[1]) if row[1] else [])
    print("  Character Tags:", json.loads(row[2]) if row[2] else [])
    print("  Series Tags:", json.loads(row[3]) if row[3] else [])

conn.close()
