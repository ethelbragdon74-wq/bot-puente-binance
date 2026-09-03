import json
import os
import threading
import time
from datetime import datetime
from flask import Flask, jsonify, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    """Ruta raíz para verificar que el servicio esté online."""
    return "🚀 El puente Webhook avanzado para trading está activo y operando.", 200

def enviar_alerta_telegram(mensaje):
    """Función segura para disparar notificaciones a Telegram."""
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    CHAT_ID = "8016135480"  # Tu Chat ID personal confirmado

    if not TOKEN:
        print("❌ Error: No se encontró TELEGRAM_BOT_TOKEN en las variables de entorno.")
        return

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown",
    }

    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"❌ Error al enviar alerta a Telegram: {e}")

def procesar_tarea_segundo_plano(datos, tiempo_inicio):
    """Procesa el guardado en Google Sheets y la notificación a Telegram fuera del ciclo principal."""
    try:
        # 1. Autenticación y conexión con Google Sheets
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        credenciales_str = os.environ.get("GOOGLE_CREDENTIALS")
        if not credenciales_str:
            print("❌ Error: No se encontró GOOGLE_CREDENTIALS en Environment.")
            return

        credenciales_dict = json.loads(credenciales_str)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(credenciales_dict, scope)
        client = gspread.authorize(creds)

        nombre_hoja = "Tracker Validación - Bot BTCUSDT 4H"
        sheet = client.open(nombre_hoja).sheet1

        # 2. Extracción de variables desde el JSON
        id_trade = str(datos.get("id", datos.get("trade_id", "TRADE-AUTO")))
        fecha_hora = str(datos.get("time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        tipo = str(datos.get("action", datos.get("type", "ALERTA")))
        
        precio_alerta = float(datos.get("price", 0))
        precio_real = float(datos.get("real_price", precio_alerta))
        
        # NUEVA VARIABLE: Extraemos el volumen inyectado por TradingView
        volumen = float(datos.get("volumen", 0))

        # 3. Cálculo de Slippage (%)
        slippage_pct = 0.0
        if precio_alerta > 0:
            if tipo.upper() in ["BUY", "COMPRA"]:
                slippage_pct = ((precio_real - precio_alerta) / precio_alerta) * 100
            else:  # SELL / VENTA
                slippage_pct = ((precio_alerta - precio_real) / precio_alerta) * 100

        slippage_str = f"{slippage_pct:.4f}%"

        # 4. Cálculo de latencia total del procesamiento
        tiempo_fin = time.time()
        latencia_ms = round((tiempo_fin - tiempo_inicio) * 1000, 2)
        latencia_str = f"{latencia_ms} ms"

        # 5. Lógica Autónoma de Crecimiento: Cálculo Dinámico de Filas, P&L y Estado
        estado = "Abierto" if tipo.upper() in ["BUY", "COMPRA"] else "Cerrado"
        
        # Encontramos la fila exacta donde se va a escribir para inyectar la fórmula perfectamente
        registros_actuales = len(sheet.get_all_values())
        siguiente_fila = registros_actuales + 1
        
        # Fórmula inyectable (Usamos IF en inglés, Google Sheets lo traduce automáticamente a SI)
        formula_pnl = f'=IF(J{siguiente_fila}="Abierto", (GOOGLEFINANCE("CURRENCY:BTCUSD") - E{siguiente_fila}) * G{siguiente_fila}, "Cerrado")'

        # 6. Inserción de la fila completa en Google Sheets
        fila = [
            id_trade,
            fecha_hora,
            tipo,
            str(precio_alerta),
            str(precio_real),
            slippage_str,
            str(volumen),       # Nueva Columna G
            formula_pnl,        # Nueva Columna H (Fórmula inyectada)
            latencia_str,       # Columna I
            estado              # Columna J
        ]

        # ¡CRÍTICO PARA STARTUPS!: value_input_option='USER_ENTERED' obliga a Sheets a ejecutar la fórmula, no a leerla como texto.
        sheet.append_row(fila, value_input_option='USER_ENTERED')
        print(f"✅ ¡Registro asíncrono exitoso en Google Sheets!: {fila}")

        # 7. Notificación a Telegram actualizada
        mensaje_alerta = (
            f"🚨 *¡Alerta de Trading con Métricas!*\n\n"
            f"📊 *ID:* {id_trade}\n"
            f"⏰ *Hora:* {fecha_hora}\n"
            f"⚡ *Acción:* {tipo}\n"
            f"🎯 *Precio Alerta:* {precio_alerta}\n"
            f"💰 *Precio Real:* {precio_real}\n"
            f"📦 *Volumen BTC:* {volumen}\n"
            f"📉 *Slippage:* {slippage_str}\n"
            f"⏱️ *Latencia:* {latencia_str}\n"
            f"🚦 *Estado:* {estado}"
        )
        enviar_alerta_telegram(mensaje_alerta)

    except Exception as e:
        print(f"❌ Error crítico en hilo secundario: {str(e)}")


@app.route("/webhook", methods=["POST"])
def webhook():
    """Ruta ultra-rápida para recibir Webhooks de TradingView."""
    tiempo_inicio = time.time()

    try:
        datos = request.get_json(silent=True)
        if not datos:
            datos = request.form.to_dict() if request.form else {}

        print("📩 Webhook recibido. Iniciando procesamiento asíncrono:", datos)

        # Disparar la lógica pesada en un hilo independiente (segundo plano)
        hilo = threading.Thread(
            target=procesar_tarea_segundo_plano, args=(datos, tiempo_inicio)
        )
        hilo.daemon = True
        hilo.start()

        # Responder de inmediato a TradingView para evitar timeouts
        return (
            jsonify({
                "status": "success",
                "message": "Alerta recibida e iniciada en segundo plano",
            }),
            200,
        )

    except Exception as e:
        print(f"❌ Error en recepción de webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto)
