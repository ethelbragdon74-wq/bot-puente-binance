import os
import json
from flask import Flask, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    """Ruta raíz para verificar que el servicio esté online."""
    return "🚀 El puente Webhook para validación de trading está activo y operando.", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    """Ruta para recibir las alertas de TradingView y registrarlas en Google Sheets."""
    try:
        # 1. Captura flexible del payload (soporta JSON o Form Data)
        datos = request.get_json(silent=True)
        if not datos:
            datos = request.form.to_dict() if request.form else {}

        print("📩 Datos recibidos en el webhook:", datos)

        # 2. Configuración de credenciales de Google Sheets
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        credenciales_str = os.environ.get("GOOGLE_CREDENTIALS")

        if not credenciales_str:
            print("❌ Error: No se encontró la variable GOOGLE_CREDENTIALS en Environment.")
            return jsonify({"status": "error", "message": "Faltan credenciales de entorno"}), 500

        # Autenticación con la Service Account
        credenciales_dict = json.loads(credenciales_str)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(credenciales_dict, scope)
        client = gspread.authorize(creds)

        # 3. Apertura de la hoja de cálculo por su nombre exacto
        nombre_hoja = "Tracker Validación - Bot BTCUSDT 4H"
        sheet = client.open(nombre_hoja).sheet1

        # 4. Mapeo de datos para las columnas de tu tablero:
        # Columna A: ID Trade
        # Columna B: Fecha/Hora
        # Columna C: Tipo (BUY/SELL/ALERTA)
        # Columna D: Precio Alerta (TV)
        id_trade = str(datos.get('id', datos.get('trade_id', 'TRADE-AUTO')))
        fecha_hora = str(datos.get('time', 'N/A'))
        tipo = str(datos.get('action', datos.get('type', 'ALERTA')))
        precio_alerta = str(datos.get('price', '0'))

        fila = [id_trade, fecha_hora, tipo, precio_alerta]

        # 5. Inserción de la fila en la hoja de cálculo
        sheet.append_row(fila)
        print(f"✅ ¡Registro exitoso en Google Sheets!: {fila}")

        return jsonify({
            "status": "success",
            "message": "Alerta registrada correctamente",
            "data_registrada": fila
        }), 200

    except Exception as e:
        print(f"❌ Error crítico en el procesamiento del webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto)
