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
    """Ruta raíz para verificar que el servicio de la Startup esté online."""
    return (
        "🚀 El puente cuantitativo MES Quant V5 con ejecución directa en Tradovate está activo.",
        200,
    )

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

def ejecutar_orden_tradovate(accion, volumen, simbolo="MESZ6"):
    """Conexión directa con la API de Tradovate para ejecutar la orden en MFFU."""
    user = os.environ.get("TRADOVATE_USER")
    password = os.environ.get("TRADOVATE_PASSWORD")
    account_id = os.environ.get("TRADOVATE_ACCOUNT_ID")
    
    # Endpoints oficiales de Tradovate para cuentas fondeadas/evaluación
    base_url = "https://live.tradovateapi.com/v1" 

    if not user or not password or not account_id:
        print("❌ Error: Faltan credenciales de Tradovate en las variables de entorno.")
        return False

    try:
        # 1. Obtener Token de Autenticación
        auth_url = f"{base_url}/auth/accesstokenstring"
        auth_payload = {
            "name": user,
            "password": password,
            "appId": "QuantV5Starter",
            "appVersion": "1.0",
            "device": "ServerRender"
        }
        
        headers = {"Content-Type": "application/json"}
        auth_response = requests.post(auth_url, json=auth_payload, headers=headers, timeout=5)
        
        if auth_response.status_code != 200:
            print(f"❌ Error de autenticación en Tradovate: {auth_response.text}")
            return False
            
        token = auth_response.text.strip().replace('"', '')
        headers_auth = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # 2. Traducir acción al formato de Tradovate (Buy / Sell)
        action_str = "Buy" if accion.upper() in ["BUY", "COMPRA", "LONG"] else "Sell"

        # 3. Enviar la orden de mercado
        order_url = f"{base_url}/order/placeorder"
        order_payload = {
            "accountSpec": account_id,
            "accountId": int(account_id),
            "action": action_str,
            "symbol": simbolo,
            "orderQty": int(volumen),
            "orderType": "Market",
            "isAutomated": True
        }

        order_response = requests.post(order_url, json=order_payload, headers=headers_auth, timeout=5)
        
        if order_response.status_code == 200:
            print(f"✅ ¡Orden ejecutada con éxito en Tradovate!: {order_response.json()}")
            return True
        else:
            print(f"❌ Error al colocar orden en Tradovate: {order_response.text}")
            return False

    except Exception as e:
        print(f"❌ Excepción crítica en API de Tradovate: {str(e)}")
        return False

def procesar_tarea_segundo_plano(datos, tiempo_inicio):
    """Procesa la ejecución en Tradovate, Google Sheets y Telegram con latencia mínima."""
    try:
        # 1. Extracción de datos del webhook o señal
        id_trade = str(datos.get("id_trade", datos.get("id", "TRADE-AUTO")))
        fecha_hora = str(datos.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        tipo = str(datos.get("accion", datos.get("action", "BUY")))
        precio_alerta = float(datos.get("precio_alerta", datos.get("price", 0)))
        volumen = int(datos.get("volumen", datos.get("contracts", 1)))
        simbolo = str(datos.get("simbolo", "MESZ6"))

        # 2. Ejecución real en el Bróker (Tradovate / MFFU)
        exito_broker = ejecutar_orden_tradovate(tipo, volumen, simbolo)
        estado_broker = "Ejecutada en Bróker" if exito_broker else "Error en Bróker"

        # 3. Autenticación y conexión con Google Sheets para auditoría
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        credenciales_str = os.environ.get("GOOGLE_CREDENTIALS")
        if credenciales_str:
            credenciales_dict = json.loads(credenciales_str)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(credenciales_dict, scope)
            client = gspread.authorize(creds)
            
            nombre_hoja = "Tracker Validación - MES Quant"
            sheet = client.open(nombre_hoja).sheet1

            registros_actuales = len(sheet.get_all_values())
            siguiente_fila = registros_actuales + 1
            formula_pnl = f'=IF(J{siguiente_fila}="Cerrado", "Calculado por Broker", "En Progreso")'

            fila = [
                id_trade,
                fecha_hora,
                tipo,
                str(precio_alerta),
                str(precio_alerta), # Precio real simulado de entrada
                "0.00%",
                str(volumen),
                formula_pnl,
                f"{round((time.time() - tiempo_inicio) * 1000, 2)} ms",
                estado_broker,
            ]
            sheet.append_row(fila, value_input_option="USER_ENTERED")

        # 4. Notificación a Telegram
        mensaje_alerta = (
            f"🚨 *¡Ejecución MES Quant V5 (Producción)*\n\n"
            f"📊 *ID:* {id_trade}\n"
            f"⏰ *Hora:* {fecha_hora}\n"
            f"⚡ *Acción:* {tipo}\n"
            f"📦 *Contratos:* {volumen}\n"
            f"🚦 *Estado:* {estado_broker}"
        )
        enviar_alerta_telegram(mensaje_alerta)

    except Exception as e:
        print(f"❌ Error crítico en hilo secundario: {str(e)}")

@app.route("/webhook", methods=["POST"])
def webhook():
    """Ruta ultra-rápida para recibir señales y ejecutar en Tradovate."""
    tiempo_inicio = time.time()

    try:
        datos = request.get_json(silent=True)
        if not datos:
            datos = request.form.to_dict() if request.form else {}

        print("📩 Señal recibida. Procesando ejecución asíncrona:", datos)

        hilo = threading.Thread(target=procesar_tarea_segundo_plano, args=(datos, tiempo_inicio))
        hilo.daemon = True
        hilo.start()

        return jsonify({"status": "success", "message": "Orden procesada hacia Tradovate"}), 200

    except Exception as e:
        print(f"❌ Error en recepción de webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto)
