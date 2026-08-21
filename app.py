import os
import json
import gspread
from flask import Flask, request, jsonify
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# Configuración de Google Sheets usando la Variable de Entorno de Render
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Leemos el contenido de la variable de entorno y lo cargamos como JSON en memoria
credenciales_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(credenciales_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Tracker Validación - Bot BTCUSDT 4H").sheet1

@app.route("/", methods=["GET"])
def home():
    return "El puente webhook de Ethel está activo y operando con éxito.", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        datos = request.get_json(silent=True)
        if not datos:
            return jsonify({"status": "error", "message": "No se recibieron datos"}), 400

        # Mapeo de los datos recibidos de TradingView
        fila = [
            "1", # ID o número de trade
            str(datos.get('time', 'N/A')),
            str(datos.get('action', 'N/A')),
            str(datos.get('price', '0'))
        ]
        
        # Escritura directa en tu Google Sheet
        sheet.append_row(fila)
        
        print(f"Registro exitoso en Google Sheets: {fila}")
        return jsonify({"status": "success", "message": "Registrado en Sheets"}), 200

    except Exception as e:
        print(f"Error procesando el webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto)
