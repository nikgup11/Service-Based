from flask import Flask, jsonify, request
from redis import Redis
import socket

app = Flask(__name__)
db = Redis(host="shop_db", port=6379, decode_responses=True)

@app.route("/balance", methods=["GET"])
def get_balance():
    # Initialize balance to 2000 if it doesn't exist
    if not db.exists("user_balance"):
        db.set("user_balance", 2000)
    
    return jsonify({
        "service": "Money Service",
        "balance": float(db.get("user_balance")),
        "instance": socket.gethostname()
    })

@app.route("/deduct", methods=["POST"])
def deduct_money():
    amount = request.json.get("amount", 0)
    current_balance = float(db.get("user_balance") or 0)

    if current_balance >= amount:
        new_balance = db.decrby("user_balance", int(amount))
        return jsonify({"success": True, "new_balance": new_balance})
    else:
        return jsonify({"success": False, "message": "Insufficient funds"}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)