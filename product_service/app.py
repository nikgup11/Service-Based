from flask import Flask, jsonify, request
from redis import Redis
import socket

app = Flask(__name__)

# Shared database
db = Redis(host="shop_db", port=6379, decode_responses=True)


def seed_products_if_needed():
    if db.exists("sku:001") == 0:
        # Added 'price' field to mapping
        db.hset("sku:001", mapping={"name": "iPhone 15 Pro", "stock": 10, "price": 999})
        db.hset("sku:002", mapping={"name": "MacBook Air", "stock": 5, "price": 1200})
        db.hset("sku:003", mapping={"name": "Sony PS5", "stock": 20, "price": 500})


@app.route("/")
def get_products():
    seed_products_if_needed()

    keys = db.keys("sku:*")
    products = {}
    for key in keys:
        products[key] = db.hgetall(key)

    return jsonify({
        "service": "Product Service",
        "bounded_context": "Inventory",
        "handled_by_instance": socket.gethostname(),
        "database": "shop_db (Shared Redis)",
        "data": products,
    })


@app.route("/reduce_stock", methods=["POST"])
def reduce_stock():
    seed_products_if_needed()
    data = request.get_json()
    sku = data.get("sku")

    if not db.exists(sku):
        return jsonify({"success": False, "message": "Product not found"}), 404

    current_stock = int(db.hget(sku, "stock"))

    if current_stock > 0:
        db.hincrby(sku, "stock", -1)
        new_stock = current_stock - 1
        return jsonify({
            "success": True,
            "product_name": db.hget(sku, "name"),
            "new_stock": new_stock,
            "price": db.hget(sku, "price")  # <--- MUST RETURN PRICE HERE
        })
    else:
        return jsonify({"success": False, "message": "Out of Stock"}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
