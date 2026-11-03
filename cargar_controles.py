import sqlite3

conn = sqlite3.connect("inventario.db")
cur = conn.cursor()

cur.execute("DELETE FROM controles")

datos = [

("Bloqueo con PIN, contraseña o biometría",
 "Técnico",
 "C",
 "Activa bloqueo automático."),

("Actualizaciones al día",
 "Técnico",
 "I",
 "Activa actualizaciones automáticas."),

("Cifrado del almacenamiento",
 "Técnico",
 "C",
 "Activa BitLocker o FileVault."),

("Antimalware activo",
 "Técnico",
 "I",
 "Mantén antivirus actualizado."),

("Respaldo automático",
 "Técnico",
 "D",
 "Implementa la regla 3-2-1."),

("MFA o Passkeys",
 "Técnico",
 "C",
 "Activa MFA en cuentas principales."),

("Contraseña de fábrica cambiada",
 "Técnico",
 "I",
 "Usa contraseña única."),

("Localización remota",
 "Técnico",
 "D",
 "Activa búsqueda remota."),

("Evito WiFi pública o uso VPN",
 "Práctico",
 "C",
 "Usa VPN en redes públicas."),

("Reviso permisos de apps",
 "Práctico",
 "C",
 "Revisa permisos periódicamente."),

("Instalo solo tiendas oficiales",
 "Práctico",
 "I",
 "Evita aplicaciones desconocidas."),

("Protección física y plan de pérdida",
 "Práctico",
 "D",
 "Define un plan de recuperación.")
]

cur.executemany("""
INSERT INTO controles
(nombre,tipo,pilar,recomendacion)
VALUES (?,?,?,?)
""", datos)

conn.commit()
conn.close()

print("Controles cargados correctamente")