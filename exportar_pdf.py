from io import BytesIO
from datetime import datetime

import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, PageBreak


def generar_pdf(df):
    if df is None:
        df = pd.DataFrame()

    if df.empty:
        df = pd.DataFrame(columns=[
            "nombre", "score", "proteccion", "riesgo_inherente", "riesgo_residual", "marca_modelo", "cliente"
        ])

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    estilos = getSampleStyleSheet()
    elementos = []

    titulo = Paragraph("TEA & TECHNOLOGY<br/>RiskGuard V5", estilos["Title"])
    elementos.append(titulo)
    elementos.append(Spacer(1, 20))

    fecha = Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", estilos["Normal"])
    elementos.append(fecha)
    elementos.append(Spacer(1, 20))

    total_activos = len(df)

    if total_activos > 0:
        score = pd.to_numeric(df.get("score", pd.Series([0] * len(df))), errors="coerce").fillna(0)
        proteccion = pd.to_numeric(df.get("proteccion", pd.Series([0] * len(df))), errors="coerce").fillna(0)

        promedio = round(score.mean(), 2)
        maximo = round(score.max(), 2)
        proteccion_promedio = round(proteccion.mean(), 2)

        score_base = (promedio * 0.70) + (maximo * 0.30)
        ajuste = min(max((total_activos - 1) * 2, 0), 30)
        score_global = round(score_base * (1 + ajuste / 100), 2)
    else:
        promedio = 0
        maximo = 0
        proteccion_promedio = 0
        score_global = 0

    resumen = f"""
    <b>Resumen Ejecutivo</b><br/><br/>
    Activos registrados: {total_activos}<br/>
    Riesgo promedio: {promedio}<br/>
    Riesgo máximo: {maximo}<br/>
    Protección promedio: {proteccion_promedio}%<br/>
    Score Global: {score_global}
    """
    elementos.append(Paragraph(resumen, estilos["BodyText"]))
    elementos.append(Spacer(1, 20))

    if score_global <= 24:
        nivel = "BAJO"
    elif score_global <= 49:
        nivel = "MEDIO"
    elif score_global <= 74:
        nivel = "ALTO"
    else:
        nivel = "CRÍTICO"

    elementos.append(Paragraph(f"<b>Nivel General:</b> {nivel}", estilos["Heading2"]))
    elementos.append(Spacer(1, 20))

    elementos.append(Paragraph("Top 5 Activos de Riesgo", estilos["Heading2"]))
    elementos.append(Spacer(1, 10))

    if total_activos > 0:
        top5 = df.copy()
        if "score" in top5.columns:
            top5["score"] = pd.to_numeric(top5["score"], errors="coerce").fillna(0)
            top5 = top5.sort_values("score", ascending=False).head(5)

        for _, fila in top5.iterrows():
            nombre = str(fila.get("nombre", "Sin nombre"))
            score_fila = fila.get("score", 0)
            proteccion_fila = fila.get("proteccion", 0)
            texto = (
                f"<b>{nombre}</b>"
                f"<br/>Score: {score_fila}"
                f"<br/>Protección: {proteccion_fila}%"
                "<br/><br/>"
            )
            elementos.append(Paragraph(texto, estilos["BodyText"]))

    elementos.append(PageBreak())

    elementos.append(Paragraph("Inventario Evaluado", estilos["Heading1"]))
    elementos.append(Spacer(1, 15))

    if total_activos > 0:
        for _, fila in df.iterrows():
            nombre = str(fila.get("nombre", "Sin nombre"))
            cliente = str(fila.get("cliente", "Sin cliente"))
            marca_modelo = str(fila.get("marca_modelo", ""))
            riesgo_inherente = fila.get("riesgo_inherente", 0)
            proteccion_fila = fila.get("proteccion", 0)
            riesgo_residual = fila.get("riesgo_residual", 0)
            score_fila = fila.get("score", 0)

            texto = f"""
            <b>{nombre}</b><br/>
            Cliente: {cliente}<br/>
            Marca/Modelo: {marca_modelo}<br/>
            Riesgo Inherente: {riesgo_inherente}<br/>
            Protección: {proteccion_fila}%<br/>
            Riesgo Residual: {riesgo_residual}<br/>
            Score: {score_fila}
            <br/><br/>
            """
            elementos.append(Paragraph(texto, estilos["BodyText"]))

    elementos.append(PageBreak())
    elementos.append(Paragraph("Recomendaciones Generales", estilos["Heading1"]))

    recomendaciones = """
    • Mantener actualizaciones activas en todos los dispositivos.<br/>
    • Activar MFA o Passkeys en servicios críticos.<br/>
    • Utilizar cifrado cuando sea posible.<br/>
    • Realizar respaldos periódicos.<br/>
    • Evitar WiFi pública sin VPN.<br/>
    • Revisar permisos de aplicaciones regularmente.<br/>
    """
    elementos.append(Paragraph(recomendaciones, estilos["BodyText"]))

    doc.build(elementos)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf