from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/process", methods=["POST"])
def process_data():
    data = request.get_json() or {}

    # Support both a "message" field or an order payload forwarded by the client
    message = data.get("message")
    if not message:
        if data.get("order_id"):
            message = f"order:{data.get('order_id')}"
        else:
            message = str(data)

    processed_message = str(message).upper()

    return jsonify({
        "original": message,
        "processed": processed_message,
        "status": "processed by processor-container"
    })

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "processor is running"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)