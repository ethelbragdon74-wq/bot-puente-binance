from flask import Flask, request
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# Configuración de Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Cargar credenciales desde el archivo secreto o variable de entorno si lo usas, 
# o asegurarnos de que lea el archivo json configurado previamente.
creds_path = 'credentials.json' # O el método que estés usando para autenticar

@app.route('/')
def home():
    return "Bot Puente Binance is Live 🚀"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Capturamos los datos que manda TradingView en formato JSON
        data = request.json
        print("Datos recibidos de TradingView:", data)
        
        if not data:
            return "No JSON received", 400

        # Extraemos variables básicas (ajusta según lo que mande tu alerta)
        ticker = data.get('ticker', 'N/A')
        action = data.get('action', 'N/A')
        price = data.get('price', '0')
        time_alert = data.get('time', 'N/A')

        # Conexión a Google Sheets para guardar el registro
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(creds)
        
        # Abrimos la hoja por su nombre exacto
        sheet = client.open("Tracker Validación - Bot BTCUSDT 4H").sheet1
        
        # Agregamos una fila con los datos
        sheet.append_row([time_alert, ticker, action, price])

        return "Success", 200

    except Exception as e:
        print(f"Error procesando el webhook: {e}")
        return str(e), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
