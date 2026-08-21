import os
import gspread
import json
from flask import Flask, request, jsonify
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# Configuración de Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
# Asegúrate de subir tu archivo JSON al repo y ponerle este nombre:
creds = ServiceAccountCredentials.from_json_keyfile_name('credenciales.json', scope)
client = gspread.authorize(creds)
sheet = client.open("Tracker Validación - Bot BTCUSDT 4H").sheet1

@app.route("/webhook", methods=["POST"])
def webhook():
    datos = request.get_json()
    if not datos:
        return jsonify({"status": "error"}), 400

    # Extraemos los datos (Asegúrate que coincidan con el JSON de TradingView)
    fila = [
        "1", # ID Trade (puedes automatizarlo después)
        datos.get('time', 'N/A'),
        datos.get('action', 'N/A'),
        datos.get('price', '0')
    ]
    
    # Escribimos en la hoja
    sheet.append_row(fila)
    
    print(f"Registro exitoso: {fila}")
    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
