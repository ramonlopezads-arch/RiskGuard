from io import BytesIO

import pandas as pd


def generar_excel(df):
    if df is None:
        df = pd.DataFrame()

    if df.empty:
        df = pd.DataFrame(columns=[
            "nombre", "marca_modelo", "categoria", "informacion",
            "cliente", "riesgo_inherente", "proteccion", "riesgo_residual", "score"
        ])

    output = BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Inventario", index=False)

        workbook = writer.book
        titulo = workbook.add_format({
            "bold": True,
            "font_size": 16,
            "bg_color": "#0F172A",
            "font_color": "white"
        })

        encabezado = workbook.add_format({
            "bold": True,
            "bg_color": "#2563EB",
            "font_color": "white"
        })

        hoja1 = writer.sheets["Inventario"]
        hoja1.write(0, 0, "RiskGuard V5 - Inventario de Riesgo", titulo)

        for col_num, value in enumerate(df.columns):
            hoja1.write(1, col_num, value, encabezado)

        hoja1.set_column(0, len(df.columns) - 1, 25)

        dashboard = workbook.add_worksheet("Dashboard")

        activos = len(df)
        if activos > 0:
            score = pd.to_numeric(df.get("score", pd.Series([0] * len(df))), errors="coerce").fillna(0)
            proteccion = pd.to_numeric(df.get("proteccion", pd.Series([0] * len(df))), errors="coerce").fillna(0)

            promedio = round(score.mean(), 2)
            maximo = round(score.max(), 2)
            proteccion_prom = round(proteccion.mean(), 2)

            score_base = (promedio * 0.70) + (maximo * 0.30)
            ajuste = min(max((activos - 1) * 2, 0), 30)
            score_global = round(score_base * (1 + ajuste / 100), 2)
        else:
            promedio = 0
            maximo = 0
            proteccion_prom = 0
            score_global = 0
            ajuste = 0

        dashboard.write("A1", "RiskGuard V5 Dashboard", titulo)
        dashboard.write("A4", "Activos")
        dashboard.write("B4", activos)
        dashboard.write("A5", "Riesgo Promedio")
        dashboard.write("B5", promedio)
        dashboard.write("A6", "Riesgo Máximo")
        dashboard.write("B6", maximo)
        dashboard.write("A7", "Protección Promedio")
        dashboard.write("B7", proteccion_prom)
        dashboard.write("A8", "Ajuste")
        dashboard.write("B8", f"{ajuste}%")
        dashboard.write("A9", "Score Global")
        dashboard.write("B9", score_global)

        if activos > 0:
            top5 = df.copy()
            if "score" in top5.columns:
                top5["score"] = pd.to_numeric(top5["score"], errors="coerce").fillna(0)
                top5 = top5.sort_values("score", ascending=False).head(5)
            top5.to_excel(writer, sheet_name="Top5", index=False)

            hoja3 = writer.sheets["Top5"]
            hoja3.write(0, 0, "Top 5 Riesgos", titulo)
            hoja3.set_column(0, len(top5.columns) - 1, 25)

    output.seek(0)
    return output.getvalue()