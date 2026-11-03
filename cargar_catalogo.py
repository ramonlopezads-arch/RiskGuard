import sqlite3

conn = sqlite3.connect("inventario.db")
cur = conn.cursor()

# Limpiar tablas
cur.execute("DELETE FROM categorias")
cur.execute("DELETE FROM informacion")

# Categorías
categorias = [
    ("Celular / smartphone", 3),
    ("Computadora portátil", 3),
    ("Computadora de escritorio", 2),
    ("Tableta", 2),
    ("Reloj inteligente", 2),
    ("Lentes inteligentes", 3),
    ("Smart TV", 2),
    ("Bocina inteligente", 2),
    ("Router / módem WiFi", 3),
    ("Cámara IP", 3),
    ("IoT del hogar", 2),
    ("Disco duro externo", 2),
    ("NAS / servidor doméstico", 3),
    ("Consola de videojuegos", 1),
    ("Impresora", 1),
    ("Vehículo conectado", 2),
    ("Otro dispositivo", 2)
]

cur.executemany(
    "INSERT INTO categorias (nombre, exposicion) VALUES (?, ?)",
    categorias
)

# Información
informacion = [
    ("Alta", 3),
    ("Media", 2),
    ("Baja", 1)
]

cur.executemany(
    "INSERT INTO informacion (nivel, valor) VALUES (?, ?)",
    informacion
)

conn.commit()
conn.close()

print("Catálogo cargado correctamente")