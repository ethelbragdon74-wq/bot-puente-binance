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
        # Intentamos capturar el JSON de TradingView de forma flexible
        datos = request.get_json(silent=True)
        if not datos:
            # Si viene como texto plano o formulario, intentamos leerlo
            datos = request.form.to_dict()
        
        print("Datos recibidos en crudo:", datos)

        # Conexión a Google Sheets usando la variable de entorno de Render
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credenciales_str = os.environ.get("GOOGLE_CREDENTIALS")
        
        if not credenciales_str:
            return jsonify({"status": "error", "message": "Faltan credenciales"}), 500
            
        credenciales_dict = json.loads(credenciales_str)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(credenciales_dict, scope)
        client = gspread.authorize(creds)
        
        # Abrimos la hoja por su nombre exacto
        sheet = client.open("Tracker Validación - Bot BTCUSDT 4H").sheet1

        # Extraemos los datos o ponemos valores por defecto para evitar que falle
        tiempo = str(datos.get('time', 'N/A'))
        ticker = str(datos.get('ticker', 'BTCUSDT'))
        accion = str(datos.get('action', 'ALERTA'))
        precio = str(datos.get('price', '0'))

        fila = [tiempo, ticker, accion, precio]
        
        sheet.append_row(fila)
        print(f"¡Éxito! Registro guardado en Google Sheets: {fila}")
        return jsonify({"status": "success", "message": "Registrado en Sheets"}), 200

    except Exception as e:
        print(f"Error crítico procesando el webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto)
