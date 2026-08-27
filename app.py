import os
import json
import threading
from flask import Flask, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    """Ruta raíz para verificar que el servicio esté online."""
    return "🚀 El puente Webhook para validación de trading está activo y operando.", 200

def enviar_alerta_telegram(mensaje):
    """Función segura para disparar notificaciones sin exponer credenciales."""
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")  # Se lee de forma segura desde Render
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
    """Función que corre en segundo plano para no bloquear la respuesta a TradingView."""
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        credenciales_str = os.environ.get("GOOGLE_CREDENTIALS")
        if not credenciales_str:
            print("❌ Error: No se encontró la variable GOOGLE_CREDENTIALS en Environment.")
            return

        # Autenticación con la Service Account
        credenciales_dict = json.loads(credenciales_str)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(credenciales_dict, scope)
        client = gspread.authorize(creds)

        # Apertura de la hoja de cálculo por su nombre exacto
        nombre_hoja = "Tracker Validación - Bot BTCUSDT 4H"
        sheet = client.open(nombre_hoja).sheet1

        # Mapeo de datos para las columnas de tu tablero
        id_trade = str(datos.get('id', datos.get('trade_id', 'TRADE-AUTO')))
        fecha_hora = str(datos.get('time', 'N/A'))
        tipo = str(datos.get('action', datos.get('type', 'ALERTA')))
        precio_alerta = str(datos.get('price', '0'))

        fila = [id_trade, fecha_hora, tipo, precio_alerta]

        # Inserción de la fila en la hoja de cálculo
        sheet.append_row(fila)
        print(f"✅ ¡Registro exitoso en Google Sheets!: {fila}")

        # 🔔 Disparamos la notificación segura a Telegram
        mensaje_alerta = f"🚨 *¡Nueva Alerta de Trading!*\n\n📊 *ID:* {id_trade}\n⏰ *Hora:* {fecha_hora}\n⚡ *Acción:* {tipo}\n💰 *Precio:* {precio_alerta}"
        enviar_alerta_telegram(mensaje_alerta)

    except Exception as e:
        print(f"❌ Error crítico en segundo plano (Google Sheets/Telegram): {str(e)}")

@app.route("/webhook", methods=["POST"])
def webhook():
    """Ruta para recibir las alertas de TradingView de forma ultrarrápida."""
    try:
        # 1. Captura flexible del payload (soporta JSON o Form Data)
        datos = request.get_json(silent=True)
        if not datos:
            datos = request.form.to_dict() if request.form else {}

        print("📩 Datos recibidos en el webhook:", datos)

        # 2. Truco de velocidad: Lanzamos el guardado y la notificación en un hilo secundario
        hilo = threading.Thread(target=guardar_en_sheets, args=(datos,))
        hilo.start()

        # 3. Respuesta instantánea a TradingView (< 100ms)
        return jsonify({
            "status": "success",
            "message": "Alerta recibida correctamente",
            "data_recibida": datos
        }), 200

    except Exception as e:
        print(f"❌ Error crítico en el procesamiento del webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto)
