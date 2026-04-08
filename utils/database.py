import sqlite3

conn = sqlite3.connect("FaceTrace.db")
cursor = conn.cursor()

columns_to_add = [
    ("age", "INTEGER"),
    ("gender", "TEXT"),
    ("marks", "TEXT"),
    ("location", "TEXT"),
    ("date", "DATE"),
    ("reporter_name", "TEXT"),
    ("relationship", "TEXT"),
    ("phone", "TEXT"),
    ("email", "TEXT"),
    ("address", "TEXT")
]

for col, col_type in columns_to_add:
    try:
        cursor.execute(f"ALTER TABLE complaints ADD COLUMN {col} {col_type}")
    except sqlite3.OperationalError:
        pass  # Column already exists

conn.commit()
conn.close()
