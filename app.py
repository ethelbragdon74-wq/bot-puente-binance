import os
import json
import threading
from flask import Flask, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    """Ruta raíz para verificar que el servicio esté online."""
    return "🚀 El puente Webhook avanzado para trading está activo y operando.", 200

def enviar_alerta_telegram(mensaje):
    """Función segura para disparar notificaciones sin exponer credenciales."""
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    CHAT_ID = "8016135480"  # Tu Chat ID personal confirmado
    
    if not TOKEN:
        print("❌ Error: No se encontró TELEGRAM_BOT_TOKEN en las variables de entorno.")
        return

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        print(f"Error al enviar alerta a Telegram: {e}")

def guardar_en_sheets(datos):
    """Función que procesa métricas avanzadas (Slippage y Latencia) y guarda en segundo plano."""
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        credenciales_str = os.environ.get("GOOGLE_CREDENTIALS")
        if not credenciales_str:
            print("❌ Error: No se encontró la variable GOOGLE_CREDENTIALS en Environment.")
            return

        credenciales_dict = json.loads(credenciales_str)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(credenciales_dict, scope)
        client = gspread.authorize(creds)

        # Apertura de la hoja de cálculo por su nombre exacto
        nombre_hoja = "Tracker Validación - Bot BTCUSDT 4H"
        sheet = client.open(nombre_hoja).sheet1

        # 1. Extracción de datos base del JSON que manda TradingView
        id_trade = str(datos.get('id', datos.get('trade_id', 'TRADE-AUTO')))
        fecha_hora = str(datos.get('time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        tipo = str(datos.get('action', datos.get('type', 'ALERTA')))
        
        # Precios para calcular el Slippage
        precio_alerta = float(datos.get('price', 0))
        precio_real = float(datos.get('real_price', precio_alerta)) # Si no viene, toma el de alerta

        # 2. Cálculo matemático del Slippage (%)
        slippage_pct = 0.0
        if precio_alerta > 0:
            if tipo.upper() in ['BUY', 'COMPRA']:
                slippage_pct = ((precio_real - precio_alerta) / precio_alerta) * 100
            else: # SELL / VENTA
                slippage_pct = ((precio_alerta - precio_real) / precio_alerta) * 100

        # Formatear a 4 decimales el porcentaje
        slippage_str = f"{slippage_pct:.4f}%"

        # Latencia (puedes medirla si envías el timestamp del cliente, o dejar un estimado)
        latencia = str(datos.get('latency', 'N/A'))

        # Armado de la fila para tu Google Sheet (Asegúrate de que tus columnas coincidan con este orden)
        # Orden sugerido: [ID, Fecha, Acción, Precio Alerta, Precio Real, Slippage, Latencia]
        fila = [id_trade, fecha_hora, tipo, str(precio_alerta), str(precio_real), slippage_str, latencia]

        sheet.append_row(fila)
        print(f"✅ ¡Registro avanzado exitoso en Google Sheets!: {fila}")

        # 🔔 Notificación mejorada a Telegram con métricas de ejecución
        mensaje_alerta = (
            f"🚨 *¡Alerta de Trading con Métricas!*\n\n"
            f"📊 *ID:* {id_trade}\n"
            f"⏰ *Hora:* {fecha_hora}\n"
            f"⚡ *Acción:* {tipo}\n"
            f"🎯 *Precio Alerta:* {precio_alerta}\n"
            f"💰 *Precio Real:* {precio_real}\n"
            f"📉 *Slippage:* {slippage_str}"
        )
        enviar_alerta_telegram(mensaje_alerta)

    except Exception as e:
        print(f"❌ Error crítico en segundo plano: {str(e)}")

@app.route("/webhook", methods=["POST"])
def webhook():
    """Ruta para recibir las alertas avanzadas de TradingView."""
    try:
        datos = request.get_json(silent=True)
        if not datos:
            datos = request.form.to_dict() if request.form else {}

        print("📩 Datos avanzados recibidos:", datos)

        hilo = threading.Thread(target=guardar_en_sheets, args=(datos,))
        hilo.start()

        return jsonify({
            "status": "success",
            "message": "Alerta avanzada procesada correctamente",
            "data_recibida": datos
        }), 200

    except Exception as e:
        print(f"❌ Error en webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto)
