import os
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "El puente webhook de Ethel está activo y operando con éxito.", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        # Recibe los datos enviados por TradingView (silent=True evita que colapse si no es un JSON válido)
        datos_alerta = request.get_json(silent=True)
        
        if not datos_alerta:
            return jsonify({"status": "error", "message": "No se recibieron datos o el formato no es JSON"}), 400

        print(f"Alerta recibida exitosamente desde TradingView: {datos_alerta}")
        
        # TODO: Aquí estructuraremos la orden directa hacia Binance en la siguiente fase
        
        return jsonify({
            "status": "success", 
            "message": "Señal procesada correctamente por el servidor propio"
        }), 200

    except Exception as e:
        print(f"Error procesando la alerta: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto)
