import os
import ccxt
from flask import Flask, request, jsonify

app = Flask(__name__)

# Inicializar conexión a Binance usando variables de entorno
exchange = ccxt.binance({
    'apiKey': os.environ.get('BINANCE_API_KEY'),
    'secret': os.environ.get('BINANCE_SECRET'),
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'}
})

@app.route("/", methods=["GET"])
def home():
    return "Bot de ejecución de Ethel activo. Puente Binance Operativo.", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        datos = request.get_json()
        if not datos:
            return jsonify({"status": "error", "message": "No se recibieron datos"}), 400

        ticker = datos.get('ticker')  # Ej: BTC/USDT
        accion = datos.get('action')  # Ej: BUY o SELL
        cantidad = float(datos.get('contracts', 0.001)) # Ajusta según tu estrategia

        print(f"Ejecutando orden: {accion} {cantidad} {ticker}")

        # Ejecución en Binance
        if accion == "BUY":
            orden = exchange.create_market_buy_order(ticker, cantidad)
        elif accion == "SELL":
            orden = exchange.create_market_sell_order(ticker, cantidad)
        else:
            return jsonify({"status": "error", "message": "Acción no reconocida"}), 400

        return jsonify({"status": "success", "order_id": orden['id']}), 200

    except Exception as e:
        print(f"Error crítico en ejecución: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto)
