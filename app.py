import os
import json
import gspread
from flask import Flask, request, jsonify
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "El puente webhook de Ethel está activo y operando con éxito.", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        # Capturamos los datos que manda TradingView
        datos = request.get_json(silent=True)
        print("Datos recibidos:", datos)
        
        if not datos:
            return jsonify({"status": "error", "message": "No se recibieron datos"}), 400

        # Conexión a Google Sheets usando la variable de entorno de Render
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Leemos las credenciales desde la variable de entorno segura
        credenciales_str = os.environ.get("GOOGLE_CREDENTIALS")
        if not credenciales_str:
            return jsonify({"status": "error", "message": "Faltan credenciales de Google en el servidor"}), 500
            
        credenciales_dict = json.loads(credenciales_str)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(credenciales_dict, scope)
        client = gspread.authorize(creds)
        
        # Abrimos la hoja por su nombre exacto
        sheet = client.open("Tracker Validación - Bot BTCUSDT 4H").sheet1

        # Mapeo y guardado de los datos en la hoja
        fila = [
            str(datos.get('time', 'N/A')),
            str(datos.get('ticker', 'N/A')),
            str(datos.get('action', 'N/A')),
            str(datos.get('price', '0'))
        ]
        
        sheet.append_row(fila)
        print(f"Registro exitoso en Google Sheets: {fila}")
        return jsonify({"status": "success", "message": "Registrado en Sheets"}), 200

    except Exception as e:
        print(f"Error procesando el webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto)
