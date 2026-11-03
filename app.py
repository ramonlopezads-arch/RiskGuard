import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from exportar_excel import generar_excel
from exportar_pdf import generar_pdf

# =====================================================
# CONFIGURACIÓN
# =====================================================
st.set_page_config(
    page_title="RiskGuard V5",
    page_icon="🛡️",
    layout="wide"
)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "inventario.db"

# =====================================================
# BD
# =====================================================
def conectar_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def tabla_existe(nombre_tabla: str) -> bool:
    conn = conectar_db()
    try:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (nombre_tabla,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def columna_existe(tabla: str, columna: str) -> bool:
    conn = conectar_db()
    try:
        columnas = conn.execute(f"PRAGMA table_info({tabla})").fetchall()
        return any(c[1] == columna for c in columnas)
    finally:
        conn.close()


def migrar_estructura_db():
    conn = conectar_db()

    # Tabla clientes
    conn.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            empresa TEXT,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Aseguramos la columna cliente_id en activos
    if tabla_existe("activos") and not columna_existe("activos", "cliente_id"):
        conn.execute("ALTER TABLE activos ADD COLUMN cliente_id INTEGER")

    # si no hay clientes, crear uno default
    clientes_total = conn.execute("SELECT COUNT(*) AS total FROM clientes").fetchone()["total"]
    if clientes_total == 0:
        conn.execute(
            "INSERT INTO clientes (nombre, empresa) VALUES (?, ?)",
            ("Cliente General", "Sin empresa")
        )

    # si hay activos sin cliente asignado, se asocian al cliente general
    conn.execute("""
        UPDATE activos
        SET cliente_id = (
            SELECT id FROM clientes WHERE nombre = 'Cliente General'
        )
        WHERE cliente_id IS NULL
    """)

    conn.commit()
    conn.close()


def inicializar_db():
    conn = conectar_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            exposicion REAL NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS informacion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nivel TEXT NOT NULL,
            valor REAL NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS controles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            orden INTEGER NOT NULL DEFAULT 0
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS activos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            marca_modelo TEXT,
            categoria_id INTEGER,
            informacion_id INTEGER,
            observaciones TEXT,
            riesgo_inherente REAL,
            proteccion REAL,
            riesgo_residual REAL,
            score REAL,
            cliente_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    categorias_total = conn.execute("SELECT COUNT(*) AS total FROM categorias").fetchone()["total"]
    if categorias_total == 0:
        conn.executemany(
            """
            INSERT INTO categorias (nombre, exposicion) VALUES (?, ?)
            """,
            [
                ("Laptop / PC", 1.2),
                ("Servidor", 1.8),
                ("Dispositivo móvil", 0.9),
                ("Red / Firewall", 2.2),
                ("Cloud / SaaS", 1.5),
                ("Periférico", 0.7),
            ]
        )

    info_total = conn.execute("SELECT COUNT(*) AS total FROM informacion").fetchone()["total"]
    if info_total == 0:
        conn.executemany(
            """
            INSERT INTO informacion (nivel, valor) VALUES (?, ?)
            """,
            [
                ("Bajo", 0.7),
                ("Medio", 1.0),
                ("Alto", 1.5),
                ("Crítico", 2.1),
            ]
        )

    controles_total = conn.execute("SELECT COUNT(*) AS total FROM controles").fetchone()["total"]
    if controles_total == 0:
        conn.executemany(
            """
            INSERT INTO controles (nombre, orden) VALUES (?, ?)
            """,
            [
                ("¿Se actualiza regularmente?", 1),
                ("¿Tiene antivirus / EDR activo?", 2),
                ("¿Cuenta con respaldo regular?", 3),
                ("¿Usa autenticación multifactor?", 4),
                ("¿Tiene acceso mínimo necesario?", 5),
                ("¿Existe control de cifrado?", 6),
                ("¿Se revisan permisos con frecuencia?", 7),
            ]
        )

    conn.commit()
    conn.close()


def leer_tabla(tabla: str) -> pd.DataFrame:
    conn = conectar_db()
    try:
        if tabla_existe(tabla):
            return pd.read_sql_query(f"SELECT * FROM {tabla}", conn)
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


def obtener_clientes():
    return leer_tabla("clientes")


def obtener_cliente_por_nombre(nombre):
    clientes = obtener_clientes()
    if clientes.empty:
        return None
    fila = clientes[clientes["nombre"] == nombre]
    if fila.empty:
        return None
    return fila.iloc[0]


def crear_cliente_si_no_existe(nombre, empresa=""):
    if not nombre or not nombre.strip():
        return None

    nombre = nombre.strip()
    clientes = obtener_clientes()

    if not clientes.empty and (clientes["nombre"].str.lower() == nombre.lower()).any():
        return clientes[clientes["nombre"].str.lower() == nombre.lower()].iloc[0]

    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO clientes (nombre, empresa) VALUES (?, ?)",
        (nombre, empresa.strip())
    )
    conn.commit()
    cliente_id = cursor.lastrowid
    conn.close()
    return {"id": cliente_id, "nombre": nombre, "empresa": empresa.strip()}


def clasificar(score):
    if pd.isna(score):
        return "🟡 Sin dato"

    if score <= 24:
        return "🟢 Bajo"
    elif score <= 49:
        return "🟡 Medio"
    elif score <= 74:
        return "🟠 Alto"
    return "🔴 Crítico"


def calcular_riesgo(exposicion, valor_info, respuestas):
    puntos = 0
    preguntas = 0

    for r in respuestas:
        if r == "No aplica":
            continue

        preguntas += 1

        if r == "Sí":
            puntos += 1
        elif r == "Parcial":
            puntos += 0.5
        elif r == "No":
            puntos += 0
        elif r == "No sé":
            puntos += 0.25

    if preguntas == 0:
        proteccion = 0
    else:
        proteccion = puntos / preguntas

    riesgo_inherente = exposicion * valor_info
    riesgo_residual = riesgo_inherente * (1 - (0.80 * proteccion))
    score = (riesgo_residual / 9) * 100

    return (
        round(riesgo_inherente, 2),
        round(proteccion * 100, 2),
        round(riesgo_residual, 2),
        round(score, 2)
    )

# =====================================================
# INICIALIZAR
# =====================================================
migrar_estructura_db()
inicializar_db()

# =====================================================
# MENÚ
# =====================================================
menu = st.sidebar.radio(
    "Menú",
    ["Dashboard", "Nuevo Activo", "Inventario"]
)

# =====================================================
# DASHBOARD
# =====================================================
if menu == "Dashboard":
    st.title("🛡️ RiskGuard V5")

    clientes = obtener_clientes()
    cliente_options = ["Todos"]
    if not clientes.empty:
        cliente_options.extend(clientes["nombre"].tolist())

    cliente_seleccionado = st.sidebar.selectbox("Cliente", cliente_options)

    df = leer_tabla("activos")

    if cliente_seleccionado != "Todos":
        cliente_id = clientes[clientes["nombre"] == cliente_seleccionado].iloc[0]["id"]
        df = df[df["cliente_id"] == cliente_id].copy() if not df.empty else df

    if df.empty:
        st.info("No existen activos registrados para este cliente.")
    else:
        df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0)
        df["proteccion"] = pd.to_numeric(df["proteccion"], errors="coerce").fillna(0)

        cantidad = len(df)
        promedio = df["score"].mean()
        maximo = df["score"].max()
        proteccion_promedio = df["proteccion"].mean()

        score_base = (promedio * 0.70) + (maximo * 0.30)
        ajuste = min(max((cantidad - 1) * 2, 0), 30)
        score_global = round(score_base * (1 + ajuste / 100), 2)

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Activos", cantidad)
        c2.metric("Riesgo Promedio", round(promedio, 2))
        c3.metric("Riesgo Máximo", round(maximo, 2))
        c4.metric("Protección Promedio", f"{round(proteccion_promedio, 2)}%")
        c5.metric("Score Global", score_global)

        st.subheader(f"Nivel General: {clasificar(score_global)}")
        st.divider()

        grafico = df.sort_values("score", ascending=False)

        fig = px.bar(
            grafico,
            x="nombre",
            y="score",
            color="score",
            text="score",
            color_continuous_scale="RdYlGn_r"
        )
        fig.update_layout(
            xaxis_title="Activo",
            yaxis_title="Score",
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

# =====================================================
# NUEVO ACTIVO
# =====================================================
elif menu == "Nuevo Activo":
    st.title("➕ Nuevo Activo")

    clientes = obtener_clientes()
    categorias = leer_tabla("categorias")
    informacion = leer_tabla("informacion")
    controles = leer_tabla("controles")

    if clientes.empty:
        crear_cliente_si_no_existe("Cliente General")

    clientes = obtener_clientes()
    clientes_nombres = clientes["nombre"].tolist()

    with st.form("form_nuevo_activo", clear_on_submit=True):
        nombre = st.text_input("Nombre del activo")
        marca_modelo = st.text_input("Marca / Modelo")

        cliente_actual = st.selectbox("Cliente", clientes_nombres)
        nuevo_cliente = st.text_input("Crear nuevo cliente (opcional)")

        categoria = st.selectbox("Categoría", categorias["nombre"].tolist())
        nivel_info = st.selectbox("Nivel de información", informacion["nivel"].tolist())
        observaciones = st.text_area("Observaciones")

        st.divider()

        opciones = ["Sí", "Parcial", "No", "No sé", "No aplica"]
        respuestas = []

        for _, control in controles.sort_values("orden").iterrows():
            resp = st.radio(
                control["nombre"],
                opciones,
                key=f"c_{control['id']}"
            )
            respuestas.append(resp)

        enviado = st.form_submit_button("💾 Guardar Evaluación", use_container_width=True)

    if enviado:
        if not nombre.strip():
            st.error("Debes escribir un nombre para el activo.")
            st.stop()

        # Crear cliente si se indicó
        cliente_final = cliente_actual
        if nuevo_cliente.strip():
            cliente_creado = crear_cliente_si_no_existe(nuevo_cliente)
            if cliente_creado:
                cliente_final = cliente_creado["nombre"]

        cliente_row = obtener_cliente_por_nombre(cliente_final)
        if cliente_row is None:
            st.error("No se pudo identificar el cliente.")
            st.stop()

        categoria_row = categorias[categorias["nombre"] == categoria].iloc[0]
        info_row = informacion[informacion["nivel"] == nivel_info].iloc[0]

        exposicion = float(categoria_row["exposicion"])
        valor_info = float(info_row["valor"])

        riesgo_inherente, proteccion, riesgo_residual, score = calcular_riesgo(
            exposicion,
            valor_info,
            respuestas
        )

        conn = conectar_db()
        conn.execute(
            """
            INSERT INTO activos (
                nombre,
                marca_modelo,
                categoria_id,
                informacion_id,
                observaciones,
                riesgo_inherente,
                proteccion,
                riesgo_residual,
                score,
                cliente_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nombre.strip(),
                marca_modelo.strip(),
                int(categoria_row["id"]),
                int(info_row["id"]),
                observaciones.strip(),
                float(riesgo_inherente),
                float(proteccion),
                float(riesgo_residual),
                float(score),
                int(cliente_row["id"])
            )
        )
        conn.commit()
        conn.close()

        st.success("Activo guardado correctamente")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Riesgo Inherente", riesgo_inherente)
        c2.metric("Protección %", proteccion)
        c3.metric("Riesgo Residual", riesgo_residual)
        c4.metric("Score", score)

        st.subheader(clasificar(score))

# =====================================================
# NUEVO ACTIVO
# =====================================================
elif menu == "Nuevo Activo":
    st.title("➕ Nuevo Activo")

    clientes = obtener_clientes()
    categorias = leer_tabla("categorias")
    informacion = leer_tabla("informacion")
    controles = leer_tabla("controles")

    if clientes.empty:
        crear_cliente_si_no_existe("Cliente General")
        clientes = obtener_clientes()

    if categorias.empty or informacion.empty or controles.empty:
        st.warning("Faltan catálogos o controles en la base de datos.")
        st.stop()

    if "orden" in controles.columns:
        controles = controles.sort_values("orden").reset_index(drop=True)
    else:
        controles = controles.reset_index(drop=True)

    clientes_nombres = clientes["nombre"].tolist()

    with st.form("form_nuevo_activo", clear_on_submit=True):
        nombre = st.text_input("Nombre del activo")
        marca_modelo = st.text_input("Marca / Modelo")

        cliente_actual = st.selectbox("Cliente", clientes_nombres)
        nuevo_cliente = st.text_input("Crear nuevo cliente (opcional)")

        categoria = st.selectbox("Categoría", categorias["nombre"].tolist())
        nivel_info = st.selectbox("Nivel de información", informacion["nivel"].tolist())
        observaciones = st.text_area("Observaciones")

        st.divider()

        opciones = ["Sí", "Parcial", "No", "No sé", "No aplica"]
        respuestas = []

        for _, control in controles.iterrows():
            resp = st.radio(
                control["nombre"],
                opciones,
                key=f"c_{control['id']}"
            )
            respuestas.append(resp)

        enviado = st.form_submit_button("💾 Guardar Evaluación", use_container_width=True)

    if enviado:
        if not nombre.strip():
            st.error("Debes escribir un nombre para el activo.")
            st.stop()

        cliente_final = cliente_actual
        if nuevo_cliente.strip():
            cliente_creado = crear_cliente_si_no_existe(nuevo_cliente)
            if cliente_creado:
                cliente_final = cliente_creado["nombre"]

        cliente_row = obtener_cliente_por_nombre(cliente_final)
        if cliente_row is None:
            st.error("No se pudo identificar el cliente.")
            st.stop()

        categoria_row = categorias[categorias["nombre"] == categoria].iloc[0]
        info_row = informacion[informacion["nivel"] == nivel_info].iloc[0]

        exposicion = float(categoria_row["exposicion"])
        valor_info = float(info_row["valor"])

        riesgo_inherente, proteccion, riesgo_residual, score = calcular_riesgo(
            exposicion,
            valor_info,
            respuestas
        )

        conn = conectar_db()
        conn.execute(
            """
            INSERT INTO activos (
                nombre,
                marca_modelo,
                categoria_id,
                informacion_id,
                observaciones,
                riesgo_inherente,
                proteccion,
                riesgo_residual,
                score,
                cliente_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nombre.strip(),
                marca_modelo.strip(),
                int(categoria_row["id"]),
                int(info_row["id"]),
                observaciones.strip(),
                float(riesgo_inherente),
                float(proteccion),
                float(riesgo_residual),
                float(score),
                int(cliente_row["id"])
            )
        )
        conn.commit()
        conn.close()

        st.success("Activo guardado correctamente")

# =====================================================
# INVENTARIO
# =====================================================
elif menu == "Inventario":
    st.title("📱 Inventario")

    clientes = obtener_clientes()
    clientes_nombres = ["Todos"]
    if not clientes.empty:
        clientes_nombres.extend(clientes["nombre"].tolist())

    cliente_filtro = st.sidebar.selectbox("Filtrar por cliente", clientes_nombres)

    sql = """
    SELECT
        a.id,
        a.nombre,
        a.marca_modelo,
        c.nombre AS categoria,
        i.nivel AS informacion,
        cl.nombre AS cliente,
        a.riesgo_inherente,
        a.proteccion,
        a.riesgo_residual,
        a.score
    FROM activos a
    LEFT JOIN categorias c ON a.categoria_id = c.id
    LEFT JOIN informacion i ON a.informacion_id = i.id
    LEFT JOIN clientes cl ON a.cliente_id = cl.id
    ORDER BY a.id DESC
    """

    conn = conectar_db()
    df = pd.read_sql_query(sql, conn)
    conn.close()

    if cliente_filtro != "Todos" and not df.empty:
        cliente_id = clientes[clientes["nombre"] == cliente_filtro].iloc[0]["id"]
        df = df[df["cliente"] == cliente_filtro].copy()

    if not df.empty:
        df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0)
        df["proteccion"] = pd.to_numeric(df["proteccion"], errors="coerce").fillna(0)
        df["nivel"] = df["score"].apply(clasificar)

    st.dataframe(df, use_container_width=True)

    if not df.empty:
        col1, col2 = st.columns(2)

        with col1:
            excel_bytes = generar_excel(df)
            st.download_button(
                label="⬇️ Descargar Excel",
                data=excel_bytes,
                file_name=f"riskguard_v5_{cliente_filtro.lower().replace(' ', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        with col2:
            pdf_bytes = generar_pdf(df)
            st.download_button(
                label="⬇️ Descargar PDF",
                data=pdf_bytes,
                file_name=f"riskguard_v5_{cliente_filtro.lower().replace(' ', '_')}.pdf",
                mime="application/pdf"
            )