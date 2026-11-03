import sqlite3

conn = sqlite3.connect("inventario.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS respuestas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    respuesta TEXT,
    puntos REAL
)
""")

cur.execute("DELETE FROM respuestas")

datos = [
    ("Sí",1),
    ("Parcial",0.5),
    ("No",0),
    ("No sé",0),
]

cur.executemany(
    "INSERT INTO respuestas(respuesta,puntos) VALUES (?,?)",
    datos
)

conn.commit()
conn.close()

print("Tabla respuestas cargada")