import sqlite3

conn = sqlite3.connect("inventario.db")
cur = conn.cursor()

cur.execute("DELETE FROM activos")

conn.commit()
conn.close()

print("Activos eliminados")